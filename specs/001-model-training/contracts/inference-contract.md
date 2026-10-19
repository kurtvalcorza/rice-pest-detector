# Contract: inference (photo to detections), as the Python reference implements it

The human-readable contract is `docs/inference-contract.md`; the reference implementation is `src/rice_pest_detector/infer.py` (45 lines). This file states what the reference does, step by step, so that a client can be checked against it. Training (`train.ManifestDataset`, `train.evaluate`), threshold choice, calibration, export parity and the app fixtures all call these two functions, so there is one implementation in Python (Principle II).

## `preprocess(image, size=640) -> np.ndarray`

| Step | Rule | Code |
| :-- | :-- | :-- |
| 1. Orientation | Apply the EXIF orientation tag first | `ImageOps.exif_transpose(image)` |
| 2. Colour | Convert to RGB (greyscale and RGBA included) | `.convert("RGB")` |
| 3. Resize | To exactly `size × size`, aspect ratio not kept, Pillow bilinear | `.resize((size, size), Image.Resampling.BILINEAR)` |
| 4. Scale | ÷ 255 to [0, 1], float32; **no** mean or std normalisation | `np.asarray(..., float32) / 255.0` |
| 5. Layout | NCHW, batch 1: `(1, 3, size, size)` | `transpose(2, 0, 1)[np.newaxis]` |

`size` is the model's `input_size` from its manifest: 640 for r50-v5 and D-FINE-L, 576 for RF-DETR-M. The exported model has a static input of that size, which tools read back with `onnx_input_size(sess)`.

## Model outputs

| Name | Shape | Meaning |
| :-- | :-- | :-- |
| `logits` | `(1, 300, 4)` | Raw class scores per query, before sigmoid |
| `pred_boxes` | `(1, 300, 4)` | Normalised `cx, cy, w, h` per query |

## `postprocess(logits, boxes, width, height, threshold=0.5) -> list[Detection]`

1. `p = 1 / (1 + exp(−logit))`, computed in float64.
2. Per query: `score = max over the 4 classes`, `class_id = argmax`.
3. Keep a query when `score >= threshold` (**inclusive**; `sigmoid(0) = 0.5` is kept at the default).
4. Boxes to corner pixels: `x0 = (cx − w/2)·width`, `y0 = (cy − h/2)·height`, `x1 = (cx + w/2)·width`, `y1 = (cy + h/2)·height`; floats, not clipped.
5. Sort by score, descending.

`width` and `height` MUST be the size of the image after EXIF transposition, not the raw `img.size`; on a rotated JPEG the raw size is swapped and boxes come out wrong without an error.

`Detection` is a frozen dataclass: `class_id`, `score`, `x0`, `y0`, `x1`, `y1`.

## Counting (outside `infer.py`)

- Species: classes 0 and 1 are rice black bug (RBB), 2 and 3 white stemborer (WSB) (`SPECIES_OF_CLASS`; `metrics.species_counts`). Counts are reported by species; sex classes only if each reaches 0.70 mAP50 on test, and the app reports species only by design.
- Threshold: each model's manifest `threshold` (r50-v5 0.48, RF-DETR-M 0.48, D-FINE-L 0.50); the 0.50 default applies only when a caller passes none.
- Review flags are an app rule, not part of this reference: a photo is flagged when a counted detection scores below the manifest's `review_below` or more than 30 insects are counted (`app/lib/counting/counting.dart`).

## How clients prove they follow it

- `tools/export_app_fixtures.py` writes `app/test/fixtures/contract_fixtures.json`: the contract constants, all 8 EXIF orientations, the Pillow-bilinear resize of 8 input shapes to 640 (SHA-256 of the whole output plus 8 sample pixels), and three postprocess cases, each with one logit of exactly 0 (score 0.5) kept at threshold 0.5. Test images are formulas, not photos: `(x·7 + y·13 + c·101 + (x·y) mod 31) mod 256`.
- `app/tool/export_resize_fixtures.py` writes `app/test/fixtures/resize_fixtures.json`: the same resize at other declared input sizes (576 for RF-DETR-M).
- Both have `--check`, and CI runs both. Pillow is pinned to 12.3.0 because Pillow 13.0 resizes some shapes differently (`docs/decisions.md`).
- Inputs under about 10 px wide make Pillow deviate by one level, so clients reject photos under 32 px a side.

## Tests

`tests/test_infer.py`: shape, range and no normalisation; greyscale and RGBA conversion; the inclusive threshold and box scaling; the `size` parameter. `tests/test_export_app_fixtures.py`: the fixtures match the package, `exif_transpose`, Pillow's resize and `postprocess`, and `--check` detects a stale file.

## Change rule

A change here changes `docs/inference-contract.md`, `infer.py`, the fixtures and every client in one change (constitution, Principle II). Consumers: [002-mobile-app](../../002-mobile-app/spec.md) (`app/lib/inference/`) and [003-desktop-app](../../003-desktop-app/spec.md).
