import json
from pathlib import Path

import numpy as np
import pytest
from PIL import Image

from rice_pest_detector.manifest import prepare


def _write(root: Path, split: str, name: str, rows: list[str], seed: int, grey: bool = False):
    img_dir = root / "02_detection_dataset" / split / "images"
    lbl_dir = root / "02_detection_dataset" / split / "labels"
    img_dir.mkdir(parents=True, exist_ok=True)
    lbl_dir.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(seed)
    pixels = rng.integers(0, 255, (64, 64, 3), dtype=np.uint8)
    if grey:
        pixels[..., 1] = pixels[..., 0]
        pixels[..., 2] = pixels[..., 0]
    Image.fromarray(pixels).save(img_dir / name)
    if rows is not None:
        (lbl_dir / (Path(name).stem + ".txt")).write_text("\n".join(rows), encoding="utf-8")


@pytest.fixture
def dataset(tmp_path: Path) -> Path:
    root = tmp_path / "with space" / "datasets"
    for i in range(40):
        rows = ["0 0.5 0.5 0.1 0.1"] if i % 3 else ["2 0.5 0.5 0.1 0.1"]
        for v in range(3):
            _write(root, "train", f"fam{i:02d}_jpg.rf.{v:032x}.jpg", rows, seed=1000 * i + v, grey=(v == 0))
    _write(root, "test", "tst01_jpg.rf.ab.jpg", ["3 0.5 0.5 0.1 0.1"], seed=9)
    _write(root, "valid", "nolabel_jpg.rf.cd.jpg", None, seed=10)
    _write(root, "train", "badbox_jpg.rf.ef.jpg", ["7 0.5 0.5 0.1 0.1"], seed=11)
    return root


def test_prepare_has_no_family_or_group_leakage(dataset: Path, tmp_path: Path):
    prepare(dataset, tmp_path / "out")
    manifest = json.loads((tmp_path / "out" / "split_manifest.json").read_text())
    by_group: dict[str, set[str]] = {}
    for rec in manifest["images"]:
        by_group.setdefault(rec["group"], set()).add(rec["split"])
    assert all(len(s) == 1 for s in by_group.values())


def test_prepare_keeps_one_colour_variant_per_eval_family(dataset: Path, tmp_path: Path):
    prepare(dataset, tmp_path / "out")
    manifest = json.loads((tmp_path / "out" / "split_manifest.json").read_text())
    evals = [r for r in manifest["images"] if r["split"] in {"val", "test"}]
    families = [r["family"] for r in evals]
    assert len(families) == len(set(families))
    assert all(r["selection_rule"] in {"published-original", "first-colour"} for r in evals)


def test_prepare_excludes_missing_label_and_invalid_box_with_reasons(dataset: Path, tmp_path: Path):
    summary = prepare(dataset, tmp_path / "out")
    exclusions = json.loads((tmp_path / "out" / "exclusions.json").read_text())
    reasons = {e["family"]: e["reason"] for e in exclusions}
    assert "missing label" in reasons["nolabel"]
    assert "class 7" in reasons["badbox"]
    assert summary["excluded_families"] == 2


def test_prepare_rejects_tray_exceeding_query_budget(dataset: Path, tmp_path: Path):
    _write(dataset, "train", "crowd_jpg.rf.aa.jpg", ["0 0.5 0.5 0.01 0.01"] * 6, seed=12)
    with pytest.raises(ValueError, match="crowd.*6 boxes.*num_queries=5"):
        prepare(dataset, tmp_path / "out", num_queries=5)


def test_prepare_writes_coco_with_one_based_categories(dataset: Path, tmp_path: Path):
    prepare(dataset, tmp_path / "out")
    coco = json.loads((tmp_path / "out" / "annotations_test.json").read_text())
    assert [c["id"] for c in coco["categories"]] == [1, 2, 3, 4]
    assert all(a["bbox"][2] > 0 for a in coco["annotations"])


def test_prepare_excludes_family_with_malformed_label_row(dataset: Path, tmp_path: Path):
    _write(dataset, "train", "ragged_jpg.rf.aa.jpg", ["0 0.5 0.5 0.1 0.1 0.2"], seed=13)
    prepare(dataset, tmp_path / "out")
    exclusions = json.loads((tmp_path / "out" / "exclusions.json").read_text())
    reasons = {e["family"]: e["reason"] for e in exclusions}
    assert reasons["ragged"].startswith("ragged_jpg.rf.aa.jpg: line 1: ")


def test_prepare_hashes_only_family_representatives(dataset: Path, tmp_path: Path):
    for fam, colour_seed in (("gxa", 7001), ("gxb", 7002)):
        _write(dataset, "train", f"{fam}_jpg.rf.{0:032x}.jpg", ["0 0.5 0.5 0.1 0.1"], seed=500, grey=True)
        _write(dataset, "train", f"{fam}_jpg.rf.{1:032x}.jpg", ["0 0.5 0.5 0.1 0.1"], seed=colour_seed)
    prepare(dataset, tmp_path / "out")
    manifest = json.loads((tmp_path / "out" / "split_manifest.json").read_text())
    group_of = {r["family"]: r["group"] for r in manifest["images"]}
    assert group_of["gxa"] != group_of["gxb"]
