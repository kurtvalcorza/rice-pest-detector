"""Ship-gate metrics: species-grouped mAP50 and per-image count accuracy."""

import contextlib
import copy
import io

import numpy as np

from rice_pest_detector import SPECIES_OF_CLASS

_SPECIES = ("RBB", "WSB")


def count_within_tolerance(pred: int, ref: int) -> bool:
    if ref < 10:
        return abs(pred - ref) <= 1
    return abs(pred - ref) <= 0.10 * ref


def species_counts(class_ids: list[int]) -> dict[str, int]:
    counts = dict.fromkeys(_SPECIES, 0)
    for c in class_ids:
        counts[SPECIES_OF_CLASS[c]] += 1
    return counts


def count_accuracy(pred_counts: list[dict[str, int]], ref_counts: list[dict[str, int]]) -> float:
    passed = [all(count_within_tolerance(p[s], r[s]) for s in _SPECIES)
              for p, r in zip(pred_counts, ref_counts, strict=True)]
    return float(np.mean(passed))


_DENSITY_BINS = ((1, 9, "1-9"), (10, 29, "10-29"), (30, None, "30+"))


def count_errors(pred_counts: list[dict[str, int]], ref_counts: list[dict[str, int]]) -> dict:
    """Per-species counting errors to read beside count_accuracy, whose +-1 tolerance below a
    reference of 10 lets an image with one insect pass when nothing is detected.

    mae: mean |pred - ref| over all images; bias: mean (pred - ref), negative = undercount;
    exact: share of images counted exactly; presence_recall: share of images containing the
    species where at least one was counted; mae_by_density: mae over images whose reference
    count falls in each bin (images without the species are excluded).
    """
    out = {}
    for s in _SPECIES:
        pairs = [(p[s], r[s]) for p, r in zip(pred_counts, ref_counts, strict=True)]
        diffs = np.array([p - r for p, r in pairs], dtype=float)
        present = [(p, r) for p, r in pairs if r > 0]
        by_density = {}
        for lo, hi, label in _DENSITY_BINS:
            sub = [abs(p - r) for p, r in present if r >= lo and (hi is None or r <= hi)]
            by_density[label] = {"images": len(sub), "mae": float(np.mean(sub)) if sub else None}
        out[s] = {"mae": float(np.abs(diffs).mean()) if pairs else None,
                  "bias": float(diffs.mean()) if pairs else None,
                  "exact": float(np.mean(diffs == 0)) if pairs else None,
                  "presence_recall": float(np.mean([p > 0 for p, _ in present])) if present else None,
                  "mae_by_density": by_density}
    return out


def _box_iou(a: list[float], b: list[float]) -> float:
    ix = max(0.0, min(a[2], b[2]) - max(a[0], b[0]))
    iy = max(0.0, min(a[3], b[3]) - max(a[1], b[1]))
    inter = ix * iy
    union = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - inter
    return inter / union if union > 0 else 0.0


def confusion(gt: list[tuple[int, list[float]]], det: list[tuple[int, list[float]]],
              iou: float = 0.5) -> dict[tuple[str, str], int]:
    from rice_pest_detector import CLASS_NAMES

    table: dict[tuple[str, str], int] = {}
    unmatched = list(range(len(gt)))
    for d_cls, d_box in det:
        best = max(unmatched, key=lambda g: _box_iou(gt[g][1], d_box), default=None)
        if best is not None and _box_iou(gt[best][1], d_box) >= iou:
            unmatched.remove(best)
            key = (CLASS_NAMES[gt[best][0]], CLASS_NAMES[d_cls])
        else:
            key = ("spurious", CLASS_NAMES[d_cls])
        table[key] = table.get(key, 0) + 1
    for g in unmatched:
        key = (CLASS_NAMES[gt[g][0]], "missed")
        table[key] = table.get(key, 0) + 1
    return table


def _to_species(coco: dict, dets: list[dict]) -> tuple[dict, list[dict]]:
    species_id = {c: 1 if SPECIES_OF_CLASS[c - 1] == "RBB" else 2 for c in range(1, 5)}
    gt = copy.deepcopy(coco)
    for a in gt["annotations"]:
        a["category_id"] = species_id[a["category_id"]]
    gt["categories"] = [{"id": 1, "name": "RBB"}, {"id": 2, "name": "WSB"}]
    return gt, [{**d, "category_id": species_id[d["category_id"]]} for d in dets]


def map50(gt_coco: dict, detections: list[dict], group_species: bool) -> dict[str, float]:
    from pycocotools.coco import COCO
    from pycocotools.cocoeval import COCOeval

    gt_dict, dets = _to_species(gt_coco, detections) if group_species else (gt_coco, detections)
    with contextlib.redirect_stdout(io.StringIO()):
        gt = COCO()
        gt.dataset = copy.deepcopy(gt_dict)
        gt.createIndex()
        dt = gt.loadRes(dets) if dets else COCO()
        ev = COCOeval(gt, dt, "bbox")
        ev.params.maxDets = [1, 10, 300]  # trays hold up to 106 insects; COCO's default cap is 100
        ev.evaluate()
        ev.accumulate()
        ev.summarize()
    result = {"all": float(ev.stats[1])}  # AP at IoU 0.50, maxDets=300
    precision = ev.eval["precision"][0, :, :, 0, -1]  # IoU=0.50, all recall, area=all, maxDets=300
    for k, cat in enumerate(gt_dict["categories"]):
        p = precision[:, k]
        result[cat["name"]] = float(p[p > -1].mean()) if (p > -1).any() else 0.0
    return result
