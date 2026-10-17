"""Calibrate an exported model's detection scores on the VALIDATION split (Platt scaling).

Run r18-1 ranks insects well (val species mAP50 0.829) but never scores above 0.25, so the
specified 0.5 threshold counts nothing. This tool labels every validation detection true or false
(greedy, score order, same species, IoU >= 0.5), fits p = sigmoid(a * logit(score) + b), and
reports the raw score where p = 0.5. Calibration is monotone, so in the app it is exactly a
threshold change: no code change, and the inference contract is untouched.

Honesty: fitting and scoring on the same images is optimistic, so every count result is also
given out-of-fold, with images grouped by family (as the splits are) into K folds. The demo
threshold (lowest count error) is re-chosen inside the same folds for a like-for-like comparison.
The test split is never read.

Run: python -m tools.calibrate_scores --onnx models/rice-pest-r18-1.onnx
         --dataset-root <riceprotek-insects-v28> --out runs/run-r18/calibration_val.json
"""

import argparse
import hashlib
import json
import random
from pathlib import Path

import numpy as np

from rice_pest_detector import SPECIES_OF_CLASS
from rice_pest_detector.metrics import _box_iou, count_accuracy, count_errors, species_counts
from tools.choose_demo_threshold import GRID, choose_threshold, onnx_input_size

FLOOR = 0.01  # detections below this raw score are dropped before fitting
EPS = 1e-6
K = 5


def _logit(s):
    s = np.clip(np.asarray(s, dtype=np.float64), EPS, 1 - EPS)
    return np.log(s / (1 - s))


def calibrate(scores, a: float, b: float) -> np.ndarray:
    return 1 / (1 + np.exp(-(a * _logit(scores) + b)))


def raw_threshold(a: float, b: float, p: float = 0.5) -> float:
    """The raw score whose calibrated probability is p."""
    z = (np.log(p / (1 - p)) - b) / a
    return float(1 / (1 + np.exp(-z)))


def fit_platt(scores, labels, l2: float = 1e-4, iters: int = 100) -> tuple[float, float]:
    """Logistic regression of labels on logit(score): damped Newton with a tiny ridge.

    Each step is halved until the penalised negative log-likelihood decreases; plain Newton
    oscillated and overflowed on the r18-1 validation scores.
    """
    x = np.stack([_logit(scores), np.ones(len(scores))], axis=1)
    y = np.asarray(labels, dtype=np.float64)

    def nll(w):
        z = x @ w
        return float(np.sum(np.logaddexp(0, z) - y * z) + 0.5 * l2 * w @ w)

    w = np.array([1.0, 0.0])
    loss = nll(w)
    for _ in range(iters):
        p = 1 / (1 + np.exp(-np.clip(x @ w, -500, 500)))
        grad = x.T @ (p - y) + l2 * w
        hess = (x * (p * (1 - p))[:, None]).T @ x + l2 * np.eye(2)
        step = np.linalg.solve(hess, grad)
        t = 1.0
        while nll(w - t * step) > loss and t > 1e-10:
            t /= 2
        w = w - t * step
        new = nll(w)
        if loss - new < 1e-12 * max(1.0, abs(loss)):
            break
        loss = new
    return float(w[0]), float(w[1])


def expected_calibration_error(probs, labels, bins: int = 10) -> float:
    probs, labels = np.asarray(probs, dtype=np.float64), np.asarray(labels, dtype=np.float64)
    idx = np.minimum((probs * bins).astype(int), bins - 1)
    total = 0.0
    for b in range(bins):
        m = idx == b
        if m.any():
            total += m.sum() * abs(probs[m].mean() - labels[m].mean())
    return float(total / len(probs))


def label_detections(gt: list[tuple[int, list[float]]], dets: list[dict], iou: float = 0.5) -> list[int]:
    """1 if a detection claims an unclaimed same-species truth box at IoU >= iou, else 0."""
    labels = [0] * len(dets)
    free = list(range(len(gt)))
    for i in sorted(range(len(dets)), key=lambda i: -dets[i]["score"]):
        d = dets[i]
        same = [g for g in free if SPECIES_OF_CLASS[gt[g][0]] == SPECIES_OF_CLASS[d["class_id"]]]
        best = max(same, key=lambda g: _box_iou(gt[g][1], d["box"]), default=None)
        if best is not None and _box_iou(gt[best][1], d["box"]) >= iou:
            free.remove(best)
            labels[i] = 1
    return labels


def family_folds(families: list[str], k: int = K, seed: int = 20261016) -> list[int]:
    unique = sorted(set(families))
    random.Random(seed).shuffle(unique)
    fold_of = {f: i % k for i, f in enumerate(unique)}
    return [fold_of[f] for f in families]


def _counts_at(images: list[dict], threshold: float) -> list[dict]:
    return [species_counts([d["class_id"] for d in im["dets"] if d["score"] >= threshold])
            for im in images]


def _expected_counts(images: list[dict], a: float, b: float) -> list[dict]:
    """Sum of calibrated probabilities per species, rounded: a count that needs no threshold."""
    out = []
    for im in images:
        p = calibrate([d["score"] for d in im["dets"]], a, b) if im["dets"] else np.array([])
        sums = {"RBB": 0.0, "WSB": 0.0}
        for d, pi in zip(im["dets"], p):
            sums[SPECIES_OF_CLASS[d["class_id"]]] += float(pi)
        out.append({s: round(v) for s, v in sums.items()})
    return out


def _count_report(preds: list[dict], refs: list[dict]) -> dict:
    errs = count_errors(preds, refs)
    return {"count_accuracy": count_accuracy(preds, refs),
            "mae_total": errs["RBB"]["mae"] + errs["WSB"]["mae"], "count_errors": errs}


def analyse(images: list[dict], k: int = K) -> dict:
    """images: [{"family", "refs", "dets": [{"class_id", "score", "box", "label"}]}]."""
    refs = [im["refs"] for im in images]
    scores = np.array([d["score"] for im in images for d in im["dets"]])
    labels = np.array([d["label"] for im in images for d in im["dets"]])
    a, b = fit_platt(scores, labels)
    t_cal = raw_threshold(a, b, 0.5)
    t_mae, _ = choose_threshold(images, GRID)

    folds = family_folds([im["family"] for im in images], k)
    oof_cal = [None] * len(images)
    oof_mae = [None] * len(images)
    oof_exp = [None] * len(images)
    oof_probs, oof_labels, fold_rows = [], [], []
    for f in range(k):
        train = [im for im, g in zip(images, folds) if g != f]
        held = [i for i, g in enumerate(folds) if g == f]
        fa, fb = fit_platt([d["score"] for im in train for d in im["dets"]],
                           [d["label"] for im in train for d in im["dets"]])
        ft = raw_threshold(fa, fb, 0.5)
        fm, _ = choose_threshold(train, GRID)
        held_images = [images[i] for i in held]
        for i, c_cal, c_mae, c_exp in zip(held, _counts_at(held_images, ft), _counts_at(held_images, fm),
                                          _expected_counts(held_images, fa, fb)):
            oof_cal[i], oof_mae[i], oof_exp[i] = c_cal, c_mae, c_exp
        for im in held_images:
            if im["dets"]:
                oof_probs += list(calibrate([d["score"] for d in im["dets"]], fa, fb))
                oof_labels += [d["label"] for d in im["dets"]]
        fold_rows.append({"fold": f, "images": len(held), "a": fa, "b": fb,
                          "calibrated_threshold": ft, "mae_threshold": fm})

    return {
        "platt": {"a": a, "b": b}, "calibrated_threshold": t_cal, "mae_threshold": t_mae,
        "detections": len(scores), "true_detections": int(labels.sum()),
        "truth_insects": int(sum(r["RBB"] + r["WSB"] for r in refs)),
        "ece": {"raw": expected_calibration_error(scores, labels),
                "calibrated_in_sample": expected_calibration_error(calibrate(scores, a, b), labels),
                "calibrated_out_of_fold": expected_calibration_error(oof_probs, oof_labels)},
        "in_sample": {"no_detection_baseline": _count_report([species_counts([]) for _ in refs], refs),
                      "specified_0.5": _count_report(_counts_at(images, 0.5), refs),
                      "calibrated_threshold": _count_report(_counts_at(images, t_cal), refs),
                      "mae_threshold": _count_report(_counts_at(images, t_mae), refs),
                      "expected_count": _count_report(_expected_counts(images, a, b), refs)},
        "out_of_fold": {"k": k, "folds": fold_rows,
                        "calibrated_threshold": _count_report(oof_cal, refs),
                        "mae_threshold": _count_report(oof_mae, refs),
                        "expected_count": _count_report(oof_exp, refs)},
    }


def _run_onnx(onnx_path: Path, records: list[dict], root: Path) -> list[dict]:
    import onnxruntime as ort
    from PIL import Image

    from rice_pest_detector.infer import postprocess, preprocess

    sess = ort.InferenceSession(str(onnx_path), providers=["CPUExecutionProvider"])
    size = onnx_input_size(sess)
    images = []
    for i, rec in enumerate(records, 1):
        with Image.open(root / rec["archive_member"]) as img:
            logits, boxes = sess.run(["logits", "pred_boxes"], {"pixel_values": preprocess(img, size)})
        found = postprocess(logits, boxes, rec["width"], rec["height"], threshold=FLOOR)
        w, h = rec["width"], rec["height"]
        gt = [(c, [(cx - bw / 2) * w, (cy - bh / 2) * h, (cx + bw / 2) * w, (cy + bh / 2) * h])
              for c, cx, cy, bw, bh in rec["boxes"]]
        dets = [{"class_id": d.class_id, "score": d.score, "box": [d.x0, d.y0, d.x1, d.y1]} for d in found]
        for d, lab in zip(dets, label_detections(gt, dets)):
            d["label"] = lab
        images.append({"file": rec["file"], "family": rec["family"],
                       "refs": species_counts([b[0] for b in rec["boxes"]]), "dets": dets})
        if i % 50 == 0:
            print(f"{i}/{len(records)} images", flush=True)
    return images


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--onnx", type=Path, required=True)
    ap.add_argument("--dataset-root", type=Path, required=True, help="folder holding datasets/...")
    ap.add_argument("--manifest", type=Path, default=Path("data/split_manifest.json"))
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--cache", type=Path, help="labelled validation detections; reused when the ONNX sha matches")
    args = ap.parse_args(argv)
    records = [r for r in json.loads(args.manifest.read_text())["images"] if r["split"] == "val"]
    sha = hashlib.sha256(args.onnx.read_bytes()).hexdigest()
    cached = json.loads(args.cache.read_text()) if args.cache and args.cache.exists() else None
    if cached and cached["onnx_sha256"] == sha and cached["floor"] == FLOOR:
        images = cached["images"]
    else:
        images = _run_onnx(args.onnx, records, args.dataset_root)
        if args.cache:
            args.cache.write_text(json.dumps({"onnx_sha256": sha, "floor": FLOOR, "images": images}),
                                  encoding="utf-8", newline="\n")
    report = {"split": "val", "images": len(records), "onnx": str(args.onnx),
              "onnx_sha256": sha, "floor": FLOOR, **analyse(images)}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=1) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({k: report[k] for k in ("platt", "calibrated_threshold", "mae_threshold", "ece")}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
