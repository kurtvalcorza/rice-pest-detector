import numpy as np
import pytest

from tools.calibrate_scores import (
    calibrate,
    expected_calibration_error,
    family_folds,
    fit_platt,
    label_detections,
    raw_threshold,
)


def det(cls, score, box):
    return {"class_id": cls, "score": score, "box": box}


BOX_A = [0, 0, 10, 10]
BOX_B = [20, 20, 30, 30]


def test_labels_match_by_species_greedily_in_score_order():
    gt = [(0, BOX_A), (2, BOX_B)]  # RBB at A, WSB at B
    dets = [det(1, 0.9, BOX_A),        # RBB_MALE on an RBB_FEMALE box: same species -> true
            det(0, 0.8, BOX_A),        # duplicate of a matched box -> false
            det(0, 0.7, BOX_B),        # wrong species at B -> false
            det(3, 0.6, [21, 21, 31, 31]),  # WSB, IoU 0.68 with B -> true
            det(2, 0.5, [40, 40, 50, 50])]  # nothing there -> false
    assert label_detections(gt, dets) == [1, 0, 0, 1, 0]


def test_labels_follow_score_order_not_list_order():
    gt = [(0, BOX_A)]
    assert label_detections(gt, [det(0, 0.2, BOX_A), det(0, 0.9, BOX_A)]) == [0, 1]


def test_platt_fit_recovers_a_known_logistic():
    rng = np.random.default_rng(0)
    scores = rng.uniform(0.01, 0.4, 20000)
    a, b = 2.0, 3.0
    labels = (rng.uniform(size=scores.size) < calibrate(scores, a, b)).astype(int)
    fa, fb = fit_platt(scores, labels)
    assert fa == pytest.approx(a, abs=0.15) and fb == pytest.approx(b, abs=0.3)


def test_raw_threshold_inverts_the_calibration():
    a, b = 2.5, 4.0
    t = raw_threshold(a, b, 0.5)
    assert 0 < t < 1
    assert calibrate(np.array([t]), a, b)[0] == pytest.approx(0.5)


def test_ece_is_zero_when_calibrated_and_large_when_not():
    probs = np.array([0.2] * 10 + [0.8] * 10)
    labels = np.array([1] * 2 + [0] * 8 + [1] * 8 + [0] * 2)
    assert expected_calibration_error(probs, labels) == pytest.approx(0.0)
    assert expected_calibration_error(np.full(20, 0.1), np.ones(20)) == pytest.approx(0.9)


def test_family_folds_keep_each_family_in_one_fold_and_are_deterministic():
    families = ["f1", "f1", "f2", "f3", "f3", "f4", "f5"]
    folds = family_folds(families, k=3)
    assert len(folds) == len(families) and set(folds) <= {0, 1, 2}
    for f in set(families):
        assert len({folds[i] for i, g in enumerate(families) if g == f}) == 1
    assert folds == family_folds(families, k=3)


def test_platt_fit_converges_on_the_r18_validation_detections():
    """Undamped Newton oscillated and overflowed on these real scores (a = -7.6e7)."""
    import json
    from pathlib import Path

    cache = Path(__file__).parents[1] / "runs" / "run-r18" / "val_dets_onnx.json"
    if not cache.exists():
        pytest.skip("validation detection cache not present (runs/ is untracked)")
    images = json.loads(cache.read_text())["images"]
    scores = [d["score"] for im in images for d in im["dets"]]
    labels = [d["label"] for im in images for d in im["dets"]]
    a, b = fit_platt(scores, labels)
    assert 0 < a < 20 and np.isfinite(b)
    assert 0.02 < raw_threshold(a, b, 0.5) < 0.1  # observed precision crosses 50% at raw 0.04-0.06


class _Input:
    def __init__(self, shape):
        self.shape = shape


class _Session:
    def __init__(self, shape):
        self._inputs = [_Input(shape)]

    def get_inputs(self):
        return self._inputs


def test_onnx_input_size_reads_the_exported_side_and_defaults_to_640():
    from tools.choose_demo_threshold import onnx_input_size

    assert onnx_input_size(_Session([1, 3, 576, 576])) == 576
    assert onnx_input_size(_Session([1, 3, 640, 640])) == 640
    assert onnx_input_size(_Session(["batch", 3, "h", "w"])) == 640
