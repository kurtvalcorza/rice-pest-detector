"""Contract rows tests/test_infer.py leaves open; each test fails if its row is broken.

Kept apart from test_infer.py because the advanced workshop's Module 6 is built on that file's four tests.
"""
import numpy as np
from PIL import Image, ImageOps

from rice_pest_detector.infer import postprocess, preprocess


def _pattern(width: int, height: int) -> Image.Image:
    y, x = np.mgrid[0:height, 0:width]
    return Image.fromarray(np.stack([(x * 7 + y * 13) % 256, (x * 3) % 256, (y * 5) % 256], axis=-1).astype(np.uint8))


def test_preprocess_applies_the_exif_orientation_first(tmp_path):
    exif = Image.Exif()
    exif[0x0112] = 6  # stored on its side
    _pattern(64, 48).save(tmp_path / "sideways.png", exif=exif)
    with Image.open(tmp_path / "sideways.png") as stored:
        upright = ImageOps.exif_transpose(stored)
        assert upright.size == (48, 64)
        assert np.array_equal(preprocess(stored), preprocess(upright))


def test_preprocess_resizes_with_pillow_bilinear():
    img = _pattern(100, 60)
    expected = np.asarray(img.resize((640, 640), Image.Resampling.BILINEAR), dtype=np.float32) / 255.0
    assert np.array_equal(preprocess(img)[0], expected.transpose(2, 0, 1))


def test_postprocess_sorts_detections_by_descending_score():
    logits = np.full((1, 300, 4), -20.0, dtype=np.float32)
    logits[0, 0, 1], logits[0, 1, 2], logits[0, 2, 3] = 1.0, 3.0, 2.0  # query order is not score order
    boxes = np.zeros((1, 300, 4), dtype=np.float32)
    dets = postprocess(logits, boxes, width=100, height=100, threshold=0.5)
    assert [d.class_id for d in dets] == [2, 3, 1]


def test_postprocess_default_threshold_is_one_half():
    logits = np.full((1, 300, 4), -20.0, dtype=np.float32)
    logits[0, 0, 1], logits[0, 1, 2] = 0.0, -0.2  # sigmoid: exactly 0.5, and about 0.45
    boxes = np.zeros((1, 300, 4), dtype=np.float32)
    assert [d.class_id for d in postprocess(logits, boxes, width=100, height=100)] == [1]
