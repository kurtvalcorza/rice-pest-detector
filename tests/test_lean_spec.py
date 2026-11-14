"""The Python code against the Lean specification in formal/ (post-processing, count tolerance,
family grouping).

formal/Fixtures.lean runs the proved specification on fixed inputs and writes
app/test/fixtures/lean_spec_fixtures.json; app/test/lean_spec_test.dart checks the Dart port
against the same file. Regenerate with `lake exe fixtures` in formal/.
"""

import json
from pathlib import Path

import numpy as np

from rice_pest_detector.dedup import group_families
from rice_pest_detector.infer import postprocess
from rice_pest_detector.metrics import count_within_tolerance

FIXTURES = Path(__file__).resolve().parents[1] / "app" / "test" / "fixtures" / "lean_spec_fixtures.json"
SPEC = json.loads(FIXTURES.read_text(encoding="utf-8"))


def _sigmoid(x: float) -> float:
    return float(1.0 / (1.0 + np.exp(-np.float64(x))))


def test_postprocess_matches_the_lean_specification():
    checked = 0
    for case in SPEC["postprocess"]:
        logits = np.array(case["logits_eighths"], dtype=np.float32)[None] / np.float32(8)
        n = logits.shape[1]
        boxes = np.zeros((1, n, 4), dtype=np.float32)
        boxes[0, :, 0] = (np.arange(n) + 0.5) / n  # cx encodes the query index
        for result in case["results"]:
            dets = postprocess(logits, boxes, n, 100, threshold=_sigmoid(result["threshold_eighths"] / 8))
            got = [[round((d.x0 + d.x1) / 2 - 0.5), d.class_id] for d in dets]
            assert got == result["expected"], (case["seed"], result["threshold_eighths"])
            checked += len(got)
    assert checked > 500  # the fixtures really exercise kept detections


def test_count_tolerance_matches_the_lean_specification():
    for band in SPEC["tolerance"]:
        ref = band["ref"]
        for pred in range(2 * ref + 3):
            assert count_within_tolerance(pred, ref) == (band["lo"] <= pred <= band["hi"]), (pred, ref)


def test_group_families_matches_the_lean_specification():
    """The Lean grouping is proved never to separate near-duplicates and never to merge
    unconnected families; the union-find must give the same groups."""
    for case in SPEC["families"]:
        got = set(group_families(case["hashes"], case["max_distance"]))
        assert got == {frozenset(g) for g in case["groups"]}, case["seed"]
