"""Write app/test/fixtures/resize_fixtures.json: Pillow BILINEAR resizes at non-default input sizes.

The main golden file (tools/export_app_fixtures.py) covers the contract default, 640. Models may
declare another square input size in their manifest (RF-DETR-M uses 576), so the Dart port of the
resampler is also checked against Pillow at those sizes. Same deterministic pattern, no photos.

Run from the repository root:  .venv/Scripts/python app/tool/export_resize_fixtures.py [--check]
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import PIL
from PIL import Image

OUT = Path(__file__).resolve().parents[1] / "test" / "fixtures" / "resize_fixtures.json"
TARGETS = (576,)
SHAPES = ((37, 23), (1000, 700), (576, 576), (640, 640), (1080, 1920), (4032, 3024), (4000, 1000))


def pattern_image(width: int, height: int) -> Image.Image:
    """RGB pattern the Dart tests rebuild: (x*7 + y*13 + c*101 + (x*y) % 31) % 256."""
    y, x, c = np.meshgrid(np.arange(height), np.arange(width), np.arange(3), indexing="ij")
    arr = ((x * 7 + y * 13 + c * 101 + (x * y) % 31) % 256).astype(np.uint8)
    return Image.fromarray(arr, "RGB")


def build() -> dict:
    cases = []
    for size in TARGETS:
        points = ((0, 0), (size - 1, 0), (0, size - 1), (size - 1, size - 1), (size // 2, size // 2),
                  (17, 401), (523, 88), (300, 1))
        for w, h in SHAPES:
            out = pattern_image(w, h).resize((size, size), Image.Resampling.BILINEAR)
            arr = np.asarray(out)
            cases.append({"size": size, "width": w, "height": h,
                          "resized_sha256": hashlib.sha256(out.tobytes()).hexdigest(),
                          "samples": [[px, py, *map(int, arr[py, px])] for px, py in points]})
    return {"generated_by": "app/tool/export_resize_fixtures.py", "pillow_version": PIL.__version__,
            "pattern": "(x*7 + y*13 + c*101 + (x*y) % 31) % 256", "resize_cases": cases}


def main(argv: list[str]) -> int:
    text = json.dumps(build(), indent=1, sort_keys=True) + "\n"
    if "--check" in argv:
        return 0 if OUT.exists() and OUT.read_text(encoding="utf-8") == text else 1
    OUT.write_text(text, encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
