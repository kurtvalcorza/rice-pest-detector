import base64
import hashlib
import json

import numpy as np
import pytest
from PIL import Image, ImageOps

from rice_pest_detector import CLASS_NAMES, SPECIES_OF_CLASS
from rice_pest_detector.infer import INPUT_SIZE, postprocess
from tools.export_app_fixtures import ORIENTATIONS, build_fixtures, pattern_image


def test_pattern_image_is_deterministic_and_matches_its_formula():
    img = pattern_image(37, 23)
    arr = np.asarray(img)
    assert arr.shape == (23, 37, 3) and arr.dtype == np.uint8
    y, x, c = 5, 11, 2
    assert arr[y, x, c] == (x * 7 + y * 13 + c * 101 + (x * y) % 31) % 256
    assert np.array_equal(arr, np.asarray(pattern_image(37, 23)))


@pytest.fixture(scope="module")
def fx():
    return build_fixtures()


def test_contract_block_matches_the_package(fx):
    c = fx["contract"]
    assert c["input_size"] == INPUT_SIZE == 640
    assert c["threshold"] == 0.5
    assert c["class_names"] == list(CLASS_NAMES)
    assert c["species_of_class"] == {str(k): v for k, v in SPECIES_OF_CLASS.items()}


def test_orientation_cases_match_pillow_exif_transpose(fx):
    assert [o["orientation"] for o in fx["orientation_cases"]] == list(ORIENTATIONS) == list(range(1, 9))
    for case in fx["orientation_cases"]:
        src = pattern_image(case["width"], case["height"])
        exif = src.getexif()
        exif[0x0112] = case["orientation"]
        src.info["exif"] = exif.tobytes()
        want = ImageOps.exif_transpose(src)
        got = base64.b64decode(case["out_rgb_b64"])
        assert (case["out_width"], case["out_height"]) == want.size
        assert got == want.convert("RGB").tobytes()
    swapped = {o["orientation"] for o in fx["orientation_cases"] if o["out_width"] != o["width"]}
    assert swapped == {5, 6, 7, 8}


def test_resize_cases_record_pillow_bilinear_output(fx):
    sizes = {(c["width"], c["height"]) for c in fx["resize_cases"]}
    # up, down, identity, phone camera shapes in both orientations, panoramas
    assert {(37, 23), (1000, 700), (640, 640), (4032, 3024), (3024, 4032), (4000, 1000), (1000, 4000)} <= sizes
    assert min(min(s) for s in sizes) >= 23  # the app rejects photos under 32 px; see MIN_SIDE in the app
    for case in fx["resize_cases"]:
        out = pattern_image(case["width"], case["height"]).resize((640, 640), Image.Resampling.BILINEAR)
        assert hashlib.sha256(out.tobytes()).hexdigest() == case["resized_sha256"]
        arr = np.asarray(out)
        for x, y, r, g, b in case["samples"]:
            assert tuple(arr[y, x]) == (r, g, b)


def test_postprocess_cases_match_the_reference_and_cover_the_boundary(fx):
    boundary_seen = False
    for case in fx["postprocess_cases"]:
        logits = np.array(case["logits"], dtype=np.float32)[None]
        boxes = np.array(case["pred_boxes"], dtype=np.float32)[None]
        assert logits.shape == boxes.shape == (1, 300, 4)
        want = postprocess(logits, boxes, case["width"], case["height"], threshold=case["threshold"])
        assert len(case["expected"]) == len(want)
        for e, d in zip(case["expected"], want):
            assert e["class_id"] == d.class_id and e["species"] == SPECIES_OF_CLASS[d.class_id]
            assert e["score"] == pytest.approx(d.score, abs=1e-12)
            assert [e["x0"], e["y0"], e["x1"], e["y1"]] == pytest.approx([d.x0, d.y0, d.x1, d.y1], abs=1e-9)
        boundary_seen |= any(e["score"] == 0.5 for e in case["expected"])
    assert boundary_seen, "a logit of exactly 0 (score 0.5) must be kept at threshold 0.5"


def test_check_mode_detects_a_stale_file(tmp_path):
    from tools.export_app_fixtures import main
    out = tmp_path / "fx.json"
    assert main(["--out", str(out)]) == 0
    assert main(["--out", str(out), "--check"]) == 0
    data = json.loads(out.read_text())
    data["contract"]["threshold"] = 0.4
    out.write_text(json.dumps(data))
    assert main(["--out", str(out), "--check"]) == 1
