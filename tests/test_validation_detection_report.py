"""Validation detection report: AP beyond IoU 0.50, and precision, recall and false positives at the threshold."""
import json

import pytest

pytest.importorskip("pycocotools")

from tools.validation_detection_report import at_threshold, coco_ap, coco_from, main

# Two 100x100 photos. Photo a: one rice black bug (class 0) and one white stemborer (class 2).
# Photo b: one rice black bug (class 1).
RECORDS = [
    {"file": "a.jpg", "split": "val", "width": 100, "height": 100,
     "boxes": [[0, 0.25, 0.25, 0.2, 0.2], [2, 0.75, 0.75, 0.2, 0.2]]},
    {"file": "b.jpg", "split": "val", "width": 100, "height": 100, "boxes": [[1, 0.5, 0.5, 0.2, 0.2]]},
]


def _perfect():
    return [
        {"file": "a.jpg", "dets": [{"class_id": 0, "score": 0.9, "box": [15, 15, 35, 35], "label": 1},
                                   {"class_id": 2, "score": 0.8, "box": [65, 65, 85, 85], "label": 1}]},
        {"file": "b.jpg", "dets": [{"class_id": 1, "score": 0.7, "box": [40, 40, 60, 60], "label": 1}]},
    ]


def test_exact_boxes_score_one_at_every_iou():
    ap = coco_ap(*coco_from(RECORDS, _perfect()))
    assert ap["all"] == pytest.approx({"ap50_95": 1.0, "ap50": 1.0, "ap75": 1.0})


def test_a_loose_box_counts_at_iou_050_but_not_at_075():
    images = _perfect()
    images[1]["dets"][0]["box"] = [40, 40, 64, 64]  # IoU with the 20x20 truth box = 400 / 576 = 0.69
    ap = coco_ap(*coco_from(RECORDS, images))
    assert ap["1"]["ap50"] == pytest.approx(1.0)
    assert ap["1"]["ap75"] == pytest.approx(0.0)
    assert ap["all"]["ap50_95"] < 1.0


def test_threshold_figures_come_from_the_labels_above_the_threshold():
    images = _perfect()
    images[0]["dets"].append({"class_id": 2, "score": 0.6, "box": [0, 60, 10, 70], "label": 0})  # false WSB
    images[1]["dets"][0]["score"] = 0.3  # below the threshold: the RBB in b is missed
    r = at_threshold(RECORDS, images, threshold=0.5)
    assert r["RBB"] == {"precision": 1.0, "recall": 0.5, "false_positives_per_image": 0.0,
                        "true_positives": 1, "false_positives": 0, "truth": 2}
    assert r["WSB"]["precision"] == pytest.approx(0.5)
    assert r["WSB"]["false_positives_per_image"] == pytest.approx(0.5)
    assert r["all"]["recall"] == pytest.approx(2 / 3)
    assert r["recall_by_density"]["RBB"]["1-9"] == {"recall": 0.5, "truth": 2}
    assert r["recall_by_density"]["WSB"]["30+"] == {"recall": None, "truth": 0}


def test_the_threshold_is_inclusive():
    r = at_threshold(RECORDS, _perfect(), threshold=0.7)
    assert r["all"]["true_positives"] == 3


def test_the_command_refuses_a_cache_for_other_photos(tmp_path):
    manifest = tmp_path / "m.json"
    manifest.write_text(json.dumps({"images": RECORDS}), encoding="utf-8")
    cache = tmp_path / "c.json"
    cache.write_text(json.dumps({"images": _perfect()[:1]}), encoding="utf-8")
    with pytest.raises(SystemExit, match="exactly the validation split"):
        main(["--cache", str(cache), "--manifest", str(manifest), "--threshold", "0.5", "--out", str(tmp_path / "o.json")])


def test_the_command_writes_a_report(tmp_path):
    manifest = tmp_path / "m.json"
    manifest.write_text(json.dumps({"images": RECORDS}), encoding="utf-8")
    cache = tmp_path / "c.json"
    cache.write_text(json.dumps({"onnx_sha256": "x", "floor": 0.01, "images": _perfect()}), encoding="utf-8")
    out = tmp_path / "o.json"
    assert main(["--cache", str(cache), "--manifest", str(manifest), "--threshold", "0.5", "--out", str(out)]) == 0
    report = json.loads(out.read_text(encoding="utf-8"))
    assert report["species"]["all"]["ap50_95"] == pytest.approx(1.0)
    assert report["at_threshold"]["all"]["recall"] == pytest.approx(1.0)
