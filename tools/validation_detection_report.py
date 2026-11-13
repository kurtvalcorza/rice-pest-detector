"""Detection metrics beyond AP50, on the validation split only.

Reads a cache of labelled validation detections written by ``tools/calibrate_scores.py --cache``
(detections down to its 0.01 score floor, each labelled 1 when it claims an unclaimed same-species
truth box at IoU >= 0.5, in descending score order) and reports:

- COCO AP averaged over IoU 0.50:0.95, AP50 and AP75, for species and for the four classes,
  with per-class values, via pycocotools with ``maxDets = [1, 10, 300]``;
- at one counting threshold: precision, recall, false positives per image, and per-species
  recall by the photo's true count of that species (1-9, 10-29, 30+).

The test split is never read. Because the floor is 0.01, AP here can sit marginally below
an AP computed with every query kept.

    python -m tools.validation_detection_report --cache <val_dets.json> --threshold 0.48 --out <report.json>
"""

import argparse
import contextlib
import copy
import io
import json
from pathlib import Path

from rice_pest_detector import SPECIES_OF_CLASS

_SPECIES = ("RBB", "WSB")
_BINS = ((1, 9, "1-9"), (10, 29, "10-29"), (30, None, "30+"))


def coco_from(records: list[dict], images: list[dict]) -> tuple[dict, list[dict]]:
    """COCO truth from the manifest records and COCO detections from the cache, in pixel xywh."""
    by_file = {r["file"]: r for r in records}
    gt = {"images": [], "annotations": [], "categories": [{"id": c + 1, "name": str(c)} for c in range(4)]}
    dets = []
    for img_id, im in enumerate(images, 1):
        rec = by_file[im["file"]]
        w, h = rec["width"], rec["height"]
        gt["images"].append({"id": img_id, "width": w, "height": h})
        for c, cx, cy, bw, bh in rec["boxes"]:
            gt["annotations"].append({"id": len(gt["annotations"]) + 1, "image_id": img_id, "category_id": c + 1,
                                      "bbox": [(cx - bw / 2) * w, (cy - bh / 2) * h, bw * w, bh * h],
                                      "area": bw * w * bh * h, "iscrowd": 0})
        for d in im["dets"]:
            x0, y0, x1, y1 = d["box"]
            dets.append({"image_id": img_id, "category_id": d["class_id"] + 1,
                         "bbox": [x0, y0, x1 - x0, y1 - y0], "score": d["score"]})
    return gt, dets


def _species(gt: dict, dets: list[dict]) -> tuple[dict, list[dict]]:
    sid = {c + 1: 1 if SPECIES_OF_CLASS[c] == "RBB" else 2 for c in range(4)}
    g = copy.deepcopy(gt)
    for a in g["annotations"]:
        a["category_id"] = sid[a["category_id"]]
    g["categories"] = [{"id": 1, "name": "RBB"}, {"id": 2, "name": "WSB"}]
    return g, [{**d, "category_id": sid[d["category_id"]]} for d in dets]


def coco_ap(gt: dict, dets: list[dict]) -> dict:
    """AP50:95, AP50 and AP75 overall and per category, at maxDets 300, area 'all'."""
    from pycocotools.coco import COCO
    from pycocotools.cocoeval import COCOeval

    with contextlib.redirect_stdout(io.StringIO()):
        g = COCO()
        g.dataset = copy.deepcopy(gt)
        g.createIndex()
        ev = COCOeval(g, g.loadRes(dets), "bbox")
        ev.params.maxDets = [1, 10, 300]  # trays hold up to 106 insects; COCO's default cap is 100
        ev.evaluate()
        ev.accumulate()
        ev.summarize()
    prec = ev.eval["precision"][:, :, :, 0, -1]  # IoU x recall x category, area all, maxDets 300

    def ap(p):
        return float(p[p > -1].mean()) if (p > -1).any() else 0.0

    # Not ev.stats[0]: summarize() reads AP50:95 at maxDets=100, which is not one of the caps set here.
    out = {"all": {"ap50_95": ap(prec), "ap50": ap(prec[0]), "ap75": ap(prec[5])}}
    for k, cat in enumerate(gt["categories"]):
        out[cat["name"]] = {"ap50_95": ap(prec[:, :, k]), "ap50": ap(prec[0, :, k]), "ap75": ap(prec[5, :, k])}
    return out


def at_threshold(records: list[dict], images: list[dict], threshold: float) -> dict:
    """Precision, recall and false positives per image at the counting threshold, from the cached labels.

    The labeller matches in descending score order, so the label of a detection at or above the
    threshold does not depend on the detections below it."""
    by_file = {r["file"]: r for r in records}
    tp = dict.fromkeys(_SPECIES, 0)
    fp = dict.fromkeys(_SPECIES, 0)
    truth = dict.fromkeys(_SPECIES, 0)
    bins = {s: {name: [0, 0] for _, _, name in _BINS} for s in _SPECIES}  # found, truth
    for im in images:
        ref = dict.fromkeys(_SPECIES, 0)
        for b in by_file[im["file"]]["boxes"]:
            ref[SPECIES_OF_CLASS[b[0]]] += 1
        found = dict.fromkeys(_SPECIES, 0)
        for d in im["dets"]:
            if d["score"] >= threshold:
                s = SPECIES_OF_CLASS[d["class_id"]]
                if d["label"]:
                    tp[s] += 1
                    found[s] += 1
                else:
                    fp[s] += 1
        for s in _SPECIES:
            truth[s] += ref[s]
            for lo, hi, name in _BINS:
                if ref[s] >= lo and (hi is None or ref[s] <= hi):
                    bins[s][name][0] += found[s]
                    bins[s][name][1] += ref[s]
    n = len(images)
    out = {"threshold": threshold, "images": n}
    for s in (*_SPECIES, "all"):
        t = sum(tp.values()) if s == "all" else tp[s]
        f = sum(fp.values()) if s == "all" else fp[s]
        g = sum(truth.values()) if s == "all" else truth[s]
        out[s] = {"precision": t / (t + f) if t + f else None, "recall": t / g if g else None,
                  "false_positives_per_image": f / n, "true_positives": t, "false_positives": f, "truth": g}
    out["recall_by_density"] = {s: {name: {"recall": f / g if g else None, "truth": g}
                                    for name, (f, g) in bins[s].items()} for s in _SPECIES}
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cache", type=Path, required=True, help="labelled validation detections from calibrate_scores.py")
    ap.add_argument("--manifest", type=Path, default=Path("data/split_manifest.json"))
    ap.add_argument("--threshold", type=float, required=True, help="the model's counting threshold")
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args(argv)
    records = [r for r in json.loads(args.manifest.read_text(encoding="utf-8"))["images"] if r["split"] == "val"]
    cache = json.loads(args.cache.read_text(encoding="utf-8"))
    images = cache["images"]
    if {im["file"] for im in images} != {r["file"] for r in records}:
        raise SystemExit("the cache does not cover exactly the validation split")
    gt, dets = coco_from(records, images)
    report = {"split": "val", "onnx_sha256": cache.get("onnx_sha256"), "floor": cache.get("floor"),
              "species": coco_ap(*_species(gt, dets)), "four_class": coco_ap(gt, dets),
              "at_threshold": at_threshold(records, images, args.threshold)}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=1) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({"species": report["species"]["all"], "at_threshold": report["at_threshold"]["all"]}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
