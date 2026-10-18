"""The committed split (data/) must hold the properties the build guarantees: no photo family and no
near-duplicate group in two splits, one image per family in validation and test, and annotation files
that list exactly the manifest's images. The other split tests use synthetic data; this one reads the
files that the notebooks and every recorded result actually used."""
import json
from collections import defaultdict
from pathlib import Path

import pytest

DATA = Path(__file__).resolve().parents[1] / "data"


@pytest.fixture(scope="module")
def manifest():
    return json.loads((DATA / "split_manifest.json").read_text(encoding="utf-8"))


def _splits_by(images, key):
    seen = defaultdict(set)
    for im in images:
        seen[im[key]].add(im["split"])
    return seen


def test_no_family_or_group_is_in_two_splits(manifest):
    for key in ("family", "group"):
        leaked = {k: v for k, v in _splits_by(manifest["images"], key).items() if len(v) > 1}
        assert not leaked, f"{len(leaked)} {key}(s) appear in more than one split"


def test_split_sizes_and_seed_match_the_record(manifest):
    counts = defaultdict(int)
    for im in manifest["images"]:
        counts[im["split"]] += 1
    assert dict(counts) == {"train": 4948, "val": 253, "test": 252}
    assert manifest["seed"] == 20261013


def test_validation_and_test_keep_one_image_per_family(manifest):
    per_family = defaultdict(int)
    for im in manifest["images"]:
        if im["split"] in ("val", "test"):
            per_family[(im["split"], im["family"])] += 1
    assert all(n == 1 for n in per_family.values())


@pytest.mark.parametrize("split", ["train", "val", "test"])
def test_annotation_files_list_exactly_the_manifest_images(manifest, split):
    coco = json.loads((DATA / f"annotations_{split}.json").read_text(encoding="utf-8"))
    in_manifest = {im["file"] for im in manifest["images"] if im["split"] == split}
    in_coco = {im["file_name"] for im in coco["images"]}
    assert in_coco == in_manifest
    boxes = sum(len(im["boxes"]) for im in manifest["images"] if im["split"] == split)
    assert len(coco["annotations"]) == boxes
