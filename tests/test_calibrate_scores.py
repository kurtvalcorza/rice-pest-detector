import numpy as np
import pytest

from tools.calibrate_scores import (
    calibrate,
    expected_calibration_error,
    family_folds,
    fit_platt,
    label_detections,
    raw_threshold,
    require_upright,
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


# ------------------------------------------------------------------ detection cache identity


def _cache_run(tmp_path, monkeypatch, records, cache_body):
    """main() on a stub model; returns True when it ran the model (the cache was not reused)."""
    import json

    from tools import calibrate_scores as cs

    onnx = tmp_path / "m.onnx"
    onnx.write_bytes(b"model bytes")
    manifest = tmp_path / "split_manifest.json"
    manifest.write_text(json.dumps({"images": records}))
    cache = tmp_path / "val_dets.json"
    if cache_body is not None:
        cache.write_text(json.dumps(cache_body(cs, records, onnx)))
    ran = []
    monkeypatch.setattr(cs, "_run_onnx", lambda *a: ran.append(1) or [])
    monkeypatch.setattr(cs, "analyse", lambda images: {"platt": {}, "calibrated_threshold": 0, "mae_threshold": 0,
                                                       "ece": {}})
    cs.main(["--onnx", str(onnx), "--dataset-root", str(tmp_path), "--manifest", str(manifest),
             "--out", str(tmp_path / "out.json"), "--cache", str(cache)])
    return bool(ran), json.loads(cache.read_text())


def _records(family="f1", box_class=0):
    return [{"file": "a.jpg", "split": "val", "family": family, "group": "g1", "width": 10, "height": 10,
             "boxes": [[box_class, 0.5, 0.5, 0.2, 0.2]]},
            {"file": "b.jpg", "split": "train", "family": "f2", "group": "g2", "width": 10, "height": 10,
             "boxes": []}]


def _sha(onnx):
    import hashlib

    return hashlib.sha256(onnx.read_bytes()).hexdigest()


def test_cache_is_reused_only_for_the_same_model_floor_labeller_and_validation_records(tmp_path, monkeypatch):
    current = lambda cs, recs, onnx: {**cs.cache_identity(_sha(onnx), [r for r in recs if r["split"] == "val"]),
                                      "images": []}
    ran, _ = _cache_run(tmp_path, monkeypatch, _records(), current)
    assert not ran


@pytest.mark.parametrize("records, change, stale", [
    (_records(family="f9"), None, "val_records_sha256"),        # family / membership changed after caching
    (_records(box_class=2), None, "val_records_sha256"),        # reference boxes changed (RBB -> WSB)
    (_records(), {"labeller_version": 0}, "labeller_version"),
    (_records(), {"floor": 0.05}, "floor"),
    (_records(), {"onnx_sha256": "0" * 64}, "onnx_sha256"),
])
def test_cache_is_refused_when_anything_it_depends_on_changed(tmp_path, monkeypatch, capsys, records, change, stale):
    def made_before(cs, recs, onnx):
        body = {**cs.cache_identity(_sha(onnx), [r for r in _records() if r["split"] == "val"]), "images": []}
        return {**body, **(change or {})}

    ran, rewritten = _cache_run(tmp_path, monkeypatch, records, made_before)
    assert ran and stale in capsys.readouterr().out
    assert rewritten["val_records_sha256"] != "" and rewritten["labeller_version"] == 1


def test_a_cache_written_before_the_identity_existed_is_refused(tmp_path, monkeypatch):
    legacy = lambda cs, recs, onnx: {"onnx_sha256": _sha(onnx), "floor": cs.FLOOR, "images": []}
    ran, rewritten = _cache_run(tmp_path, monkeypatch, _records(), legacy)
    assert ran and set(rewritten) >= {"labeller_version", "val_records_sha256"}


def _photo(tmp_path, size=(64, 48), orientation=None):
    from PIL import Image

    exif = Image.Exif()
    if orientation is not None:
        exif[0x0112] = orientation
    Image.new("RGB", size).save(tmp_path / "p.jpg", exif=exif)
    return Image.open(tmp_path / "p.jpg")


REC = {"file": "p.jpg", "width": 64, "height": 48}


@pytest.mark.parametrize("orientation", [None, 1])
def test_an_upright_photo_of_the_recorded_size_passes(tmp_path, orientation):
    with _photo(tmp_path, orientation=orientation) as img:
        require_upright(img, REC)


@pytest.mark.parametrize("orientation", [2, 3, 4, 5, 6, 7, 8])
def test_any_exif_rotation_or_flip_is_refused(tmp_path, orientation):
    with _photo(tmp_path, orientation=orientation) as img, pytest.raises(ValueError, match=f"orientation {orientation}"):
        require_upright(img, REC)


def test_a_size_that_differs_from_the_manifest_is_refused(tmp_path):
    with _photo(tmp_path, size=(48, 64)) as img, pytest.raises(ValueError, match="size 48x64, manifest 64x48"):
        require_upright(img, REC)
