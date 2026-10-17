"""YOLO-format label parsing and validation."""

import math
from dataclasses import dataclass
from pathlib import Path

from rice_pest_detector import CLASS_NAMES

_EPS = 1e-6


@dataclass(frozen=True)
class Box:
    class_id: int
    cx: float
    cy: float
    w: float
    h: float


def parse_labels(text: str) -> list[Box]:
    boxes: list[Box] = []
    for number, line in enumerate(text.splitlines(), start=1):
        fields = line.split()
        if not fields:
            continue
        if len(fields) == 5:
            boxes.append(Box(int(fields[0]), *(float(v) for v in fields[1:])))
        elif len(fields) >= 7 and len(fields) % 2 == 1:
            # YOLO-seg polygon: class id followed by x,y pairs -> min/max bounding box.
            values = [float(v) for v in fields[1:]]
            xs, ys = values[0::2], values[1::2]
            boxes.append(Box(int(fields[0]), (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2,
                             max(xs) - min(xs), max(ys) - min(ys)))
        else:
            raise ValueError(f"line {number}: expected 5 fields or an odd polygon row, got {len(fields)}")
    return boxes


def validate_boxes(boxes: list[Box]) -> list[str]:
    errors: list[str] = []
    for i, b in enumerate(boxes):
        if not 0 <= b.class_id < len(CLASS_NAMES):
            errors.append(f"box {i}: class {b.class_id} not in 0..{len(CLASS_NAMES) - 1}")
        elif not all(math.isfinite(v) for v in (b.cx, b.cy, b.w, b.h)):
            errors.append(f"box {i}: non-finite coordinate")
        elif b.w <= 0 or b.h <= 0:
            errors.append(f"box {i}: non-positive area")
        elif (b.cx - b.w / 2 < -_EPS or b.cx + b.w / 2 > 1 + _EPS
              or b.cy - b.h / 2 < -_EPS or b.cy + b.h / 2 > 1 + _EPS):
            errors.append(f"box {i}: extends outside the image")
    return errors


def load_label_file(path: Path) -> list[Box]:
    return parse_labels(Path(path).read_text(encoding="utf-8"))
