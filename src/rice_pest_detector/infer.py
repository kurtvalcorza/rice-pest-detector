"""Inference contract shared by export parity checks and downstream tools."""

from dataclasses import dataclass

import numpy as np
from PIL import Image, ImageOps

INPUT_SIZE = 640


@dataclass(frozen=True)
class Detection:
    class_id: int
    score: float
    x0: float
    y0: float
    x1: float
    y1: float


def preprocess(image: Image.Image, size: int = INPUT_SIZE) -> np.ndarray:
    """size is the model input side; the app contract is 640 (RF-DETR-M trains at 576)."""
    rgb = ImageOps.exif_transpose(image).convert("RGB")
    resized = rgb.resize((size, size), Image.Resampling.BILINEAR)
    array = np.asarray(resized, dtype=np.float32) / 255.0
    return array.transpose(2, 0, 1)[np.newaxis].copy()


def postprocess(logits: np.ndarray, boxes: np.ndarray, width: int, height: int,
                threshold: float = 0.5) -> list[Detection]:
    """Turn raw RT-DETR outputs into detections in original-image pixels.

    ``width`` and ``height`` MUST be the size of the EXIF-transposed image
    (``ImageOps.exif_transpose(img).size``), not the raw ``img.size``; otherwise
    boxes are wrong on rotated JPEGs.
    """
    probs = 1.0 / (1.0 + np.exp(-logits[0].astype(np.float64)))
    scores, classes = probs.max(axis=1), probs.argmax(axis=1)
    detections = []
    for q in np.nonzero(scores >= threshold)[0]:
        cx, cy, w, h = boxes[0, q].astype(np.float64)
        detections.append(Detection(int(classes[q]), float(scores[q]),
                                    float((cx - w / 2) * width), float((cy - h / 2) * height),
                                    float((cx + w / 2) * width), float((cy + h / 2) * height)))
    return sorted(detections, key=lambda d: -d.score)
