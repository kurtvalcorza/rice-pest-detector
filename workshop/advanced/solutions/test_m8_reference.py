"""Reference answer to Module 8's practice issue. A learner's version goes in tests/test_infer_issue.py.

Tests only: they pass against the unchanged infer.py, and change no threshold, contract text or fixture.
"""
import numpy as np
import pytest
from PIL import Image, ImageOps

from rice_pest_detector.infer import postprocess

PUBLISHED_THRESHOLD = 0.48  # app/assets/model_catalog.json


def test_a_score_at_a_published_threshold_is_kept():
    logits = np.full((1, 300, 4), -20.0, dtype=np.float64)
    logits[0, 0, 1] = np.log(PUBLISHED_THRESHOLD / (1 - PUBLISHED_THRESHOLD))
    boxes = np.zeros((1, 300, 4), dtype=np.float32)
    score = 1.0 / (1.0 + np.exp(-logits[0, 0, 1]))  # exact to the last bit, unlike the literal 0.48
    assert score == pytest.approx(PUBLISHED_THRESHOLD)
    assert [d.class_id for d in postprocess(logits, boxes, width=100, height=100, threshold=score)] == [1]


def test_boxes_scale_by_the_orientation_corrected_size(tmp_path):
    exif = Image.Exif()
    exif[0x0112] = 6  # stored on its side: 64 wide and 48 high in the file, 48 by 64 upright
    Image.new("RGB", (64, 48)).save(tmp_path / "sideways.jpg", exif=exif)
    with Image.open(tmp_path / "sideways.jpg") as stored:
        width, height = ImageOps.exif_transpose(stored).size
    logits = np.full((1, 300, 4), -20.0, dtype=np.float32)
    logits[0, 0, 0] = 5.0
    boxes = np.zeros((1, 300, 4), dtype=np.float32)
    boxes[0, 0] = [0.5, 0.5, 0.25, 0.25]
    [d] = postprocess(logits, boxes, width=width, height=height)
    assert (d.x0, d.y0, d.x1, d.y1) == pytest.approx((18.0, 24.0, 30.0, 40.0))
