"""Choose a DEMO counting threshold for an exported model on the VALIDATION split only.

Run r18-1 never scores a detection >= 0.5, so the shipping threshold counts nothing. This tool
runs the ONNX model on validation images, sweeps thresholds, and picks the one with the lowest
total per-image count error (rice black bug + white stemborer), preferring the higher threshold
on ties. The test split is never read. The result is a demo setting, not a shipping decision.

Run: python -m tools.choose_demo_threshold --onnx models/rice-pest-r18-1.onnx
         --dataset-root <riceprotek-insects-v28> --out runs/run-r18/demo_threshold.json
"""

import argparse
import json
import sys
from pathlib import Path

import numpy as np

from rice_pest_detector import SPECIES_OF_CLASS
from rice_pest_detector.metrics import count_accuracy, count_errors, species_counts

GRID = [round(t, 2) for t in np.arange(0.02, 0.51, 0.02)] + [0.5]
GRID = sorted(set(GRID))
FLOOR = 0.01  # cached detections below this are dropped


def sweep(images: list[dict], grid: list[float]) -> list[dict]:
    """images: [{"refs": {"RBB": n, "WSB": n}, "dets": [{"class_id", "score"}]}]."""
    refs = [im["refs"] for im in images]
    rows = []
    for t in grid:
        preds = [species_counts([d["class_id"] for d in im["dets"] if d["score"] >= t]) for im in images]
        errs = count_errors(preds, refs)
        rows.append({"threshold": t, "mae_total": sum(errs[s]["mae"] for s in ("RBB", "WSB")),
                     "count_accuracy": count_accuracy(preds, refs), "count_errors": errs,
                     "detections_kept": sum(sum(p.values()) for p in preds)})
    return rows


def choose_threshold(images: list[dict], grid: list[float] = GRID) -> tuple[float, list[dict]]:
    rows = sweep(images, grid)
    best = min(rows, key=lambda r: (round(r["mae_total"], 9), -r["threshold"]))
    return best["threshold"], rows


def onnx_input_size(sess) -> int:
    """The square input size baked into an exported model (640 for RT-DETR, 576 for RF-DETR-M)."""
    side = sess.get_inputs()[0].shape[-1]
    return side if isinstance(side, int) else 640


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
        images.append({"file": rec["file"], "refs": species_counts([b[0] for b in rec["boxes"]]),
                       "dets": [{"class_id": d.class_id, "score": d.score} for d in found]})
        if i % 50 == 0:
            print(f"{i}/{len(records)} images", flush=True)
    return images


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--onnx", type=Path, required=True)
    ap.add_argument("--dataset-root", type=Path, required=True, help="folder holding datasets/...")
    ap.add_argument("--manifest", type=Path, default=Path("data/split_manifest.json"))
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args(argv)
    records = [r for r in json.loads(args.manifest.read_text())["images"] if r["split"] == "val"]
    images = _run_onnx(args.onnx, records, args.dataset_root)
    best, rows = choose_threshold(images)
    top = [d["score"] for im in images for d in im["dets"][:1]]
    report = {"split": "val", "images": len(images), "onnx": str(args.onnx), "chosen_threshold": best,
              "top_score_per_image": {"p50": float(np.median(top)) if top else 0.0,
                                      "max": float(max(top)) if top else 0.0},
              "sweep": rows, "species": dict(SPECIES_OF_CLASS)}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=1) + "\n", encoding="utf-8")
    print(f"chosen demo threshold {best}")
    for r in rows:
        if r["threshold"] in (0.1, 0.2, 0.3, 0.4, 0.5) or r["threshold"] == best:
            print(f"  t={r['threshold']:.2f}  count MAE {r['mae_total']:.2f}  "
                  f"count acc {r['count_accuracy']:.3f}  kept {r['detections_kept']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
