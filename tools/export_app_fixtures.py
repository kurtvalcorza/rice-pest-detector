"""Write golden fixtures that the demonstration app (app/) must reproduce bit for bit or to 1e-9.

No photos are committed: every test image is a deterministic pattern that the Dart tests regenerate
from the same formula. Run: python -m tools.export_app_fixtures [--out PATH] [--check]
"""

import argparse
import base64
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import PIL
from PIL import Image, ImageOps

from rice_pest_detector import CLASS_NAMES, SPECIES_OF_CLASS
from rice_pest_detector.infer import INPUT_SIZE, postprocess

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "app" / "test" / "fixtures" / "contract_fixtures.json"
ORIENTATIONS = tuple(range(1, 9))
# Inputs under ~10 px wide make Pillow 12.3 deviate from a horizontal-first pass by one level; no
# camera produces them, so the app rejects photos under 32 px a side and these cases cover real shapes.
RESIZE_SIZES = ((37, 23), (1000, 700), (640, 640), (1080, 1920),
                (4032, 3024), (3024, 4032), (4000, 1000), (1000, 4000))
SAMPLE_POINTS = ((0, 0), (639, 0), (0, 639), (639, 639), (320, 320), (17, 401), (523, 88), (300, 1))


def pattern_image(width: int, height: int) -> Image.Image:
    """RGB pattern the Dart tests rebuild: (x*7 + y*13 + c*101 + (x*y) % 31) % 256."""
    y, x, c = np.mgrid[0:height, 0:width, 0:3]
    arr = ((x * 7 + y * 13 + c * 101 + (x * y) % 31) % 256).astype(np.uint8)
    return Image.fromarray(arr, "RGB")


def _b64(data: bytes) -> str:
    return base64.b64encode(data).decode("ascii")


def _orientation_cases() -> list[dict]:
    cases = []
    for k in ORIENTATIONS:
        src = pattern_image(5, 3)
        src.getexif()[0x0112] = k
        out = ImageOps.exif_transpose(src).convert("RGB")
        cases.append({"orientation": k, "width": 5, "height": 3, "out_width": out.size[0],
                      "out_height": out.size[1], "out_rgb_b64": _b64(out.tobytes())})
    return cases


def _resize_cases() -> list[dict]:
    cases = []
    for w, h in RESIZE_SIZES:
        out = pattern_image(w, h).resize((INPUT_SIZE, INPUT_SIZE), Image.Resampling.BILINEAR)
        arr = np.asarray(out)
        cases.append({"width": w, "height": h,
                      "resized_sha256": hashlib.sha256(out.tobytes()).hexdigest(),
                      "samples": [[x, y, *map(int, arr[y, x])] for x, y in SAMPLE_POINTS]})
    return cases


def _postprocess_cases() -> list[dict]:
    rng = np.random.default_rng(20261015)
    cases = []
    for name, (w, h) in (("square", (640, 640)), ("landscape", (4000, 3000)), ("portrait", (1080, 1920))):
        logits = rng.normal(-6.0, 1.5, size=(300, 4)).astype(np.float32)
        hot = rng.choice(300, size=12, replace=False)
        logits[hot, rng.integers(0, 4, size=12)] = rng.uniform(-1.0, 4.0, size=12).astype(np.float32)
        logits[7] = np.float32(-8.0)
        logits[7, 2] = np.float32(0.0)  # score exactly 0.5: kept at threshold 0.5
        boxes = np.column_stack([rng.uniform(0.05, 0.95, 300), rng.uniform(0.05, 0.95, 300),
                                 rng.uniform(0.01, 0.2, 300), rng.uniform(0.01, 0.2, 300)]).astype(np.float32)
        found = postprocess(logits[None], boxes[None], w, h, threshold=0.5)
        cases.append({"name": name, "width": w, "height": h, "threshold": 0.5,
                      "logits": [[float(v) for v in row] for row in logits],
                      "pred_boxes": [[float(v) for v in row] for row in boxes],
                      "expected": [{"class_id": d.class_id, "species": SPECIES_OF_CLASS[d.class_id],
                                    "score": d.score, "x0": d.x0, "y0": d.y0, "x1": d.x1, "y1": d.y1}
                                   for d in found]})
    return cases


def build_fixtures() -> dict:
    return {"generated_by": "tools/export_app_fixtures.py", "pillow_version": PIL.__version__,
            "pattern": "(x*7 + y*13 + c*101 + (x*y) % 31) % 256",
            "contract": {"input_size": INPUT_SIZE, "threshold": 0.5, "class_names": list(CLASS_NAMES),
                         "species_of_class": {str(k): v for k, v in SPECIES_OF_CLASS.items()}},
            "orientation_cases": _orientation_cases(), "resize_cases": _resize_cases(),
            "postprocess_cases": _postprocess_cases()}


def _serialise(fx: dict) -> str:
    return json.dumps(fx, indent=1, sort_keys=True) + "\n"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--check", action="store_true", help="exit 1 if --out differs from a fresh build")
    args = ap.parse_args(argv)
    text = _serialise(build_fixtures())
    if args.check:
        return 0 if args.out.exists() and args.out.read_text(encoding="utf-8") == text else 1
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(text, encoding="utf-8", newline="\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
