import numpy as np
import pytest
from PIL import Image

from rice_pest_detector.infer import Detection, postprocess, preprocess


def test_preprocess_shape_range_and_no_normalisation():
    img = Image.new("RGB", (1280, 960), (255, 0, 0))
    x = preprocess(img)
    assert x.shape == (1, 3, 640, 640) and x.dtype == np.float32
    assert np.allclose(x[0, 0], 1.0) and np.allclose(x[0, 1], 0.0)


def test_preprocess_converts_greyscale_and_rgba():
    assert preprocess(Image.new("L", (10, 10), 128)).shape == (1, 3, 640, 640)
    assert preprocess(Image.new("RGBA", (10, 10))).shape == (1, 3, 640, 640)


def test_postprocess_threshold_is_inclusive_and_scales_boxes():
    logits = np.full((1, 300, 4), -20.0, dtype=np.float32)
    logits[0, 0, 2] = 0.0          # sigmoid = exactly 0.5
    logits[0, 1, 1] = -0.01        # just below 0.5
    boxes = np.zeros((1, 300, 4), dtype=np.float32)
    boxes[0, 0] = [0.5, 0.5, 0.2, 0.1]
    dets = postprocess(logits, boxes, width=200, height=100, threshold=0.5)
    assert len(dets) == 1 and isinstance(dets[0], Detection)
    d = dets[0]
    assert d.class_id == 2 and d.score == 0.5  # sigmoid(0) is exactly 0.5: the >= boundary
    assert (d.x0, d.y0, d.x1, d.y1) == pytest.approx((80.0, 45.0, 120.0, 55.0), abs=1e-4)


def test_preprocess_takes_a_model_input_size():
    out = preprocess(Image.new("RGB", (100, 60), (10, 20, 30)), size=576)
    assert out.shape == (1, 3, 576, 576)
    assert preprocess(Image.new("RGB", (100, 60))).shape == (1, 3, 640, 640)  # contract default
