# Inference Contract

This document is the human-readable contract for the rice-pest detectors (RT-DETR r50-v5, RF-DETR-M and D-FINE-L) at inference time. The reference implementation is `src/rice_pest_detector/infer.py`. The demo app (`app/lib/inference/`) reproduces this contract, so any change here must be mirrored there.

## Input

| Property | Value |
| :--- | :--- |
| Tensor name | `pixel_values` |
| Dtype | float32 |
| Shape | `(1, 3, S, S)` (batch, channels, height, width); S = the model's `input_size`: 640 by default, 576 for RF-DETR-M |
| Channel order | RGB |
| Orientation | EXIF-transposed before any other step |
| Resize | Bilinear to S × S (PIL `Image.Resampling.BILINEAR`); aspect ratio is not preserved |
| Scaling | Divide by 255, giving values in [0, 1] |
| Normalisation | **None.** No mean or std subtraction (`do_normalize: false`) |

Greyscale and RGBA inputs are converted to RGB before resizing.

## Outputs

| Name | Shape | Meaning |
| :--- | :--- | :--- |
| `logits` | `(1, 300, 4)` | One raw score per query per class, before sigmoid |
| `pred_boxes` | `(1, 300, 4)` | One box per query, normalised `cx, cy, w, h` (each in [0, 1] of the input image) |

The model emits 300 queries (`num_queries = 300`). Most queries are low-scoring and are removed by the threshold.

## Scoring

1. Apply the sigmoid to every logit (computed in float64): `p = 1 / (1 + exp(-logit))`.
2. For each query, take the maximum over the four classes: `score = max_c p[c]`, and the predicted class is the argmax.
3. Keep a query only if `score >= threshold`. The comparison is **inclusive**.
4. The default threshold in `infer.py` is **0.50**. Callers may pass another value; each published model's manifest sets its own counting threshold (r50-v5 0.48, RF-DETR-M 0.48, D-FINE-L 0.50), and the app uses that.
5. Sort the kept detections by score, descending.

Because `sigmoid(0)` is exactly 0.5, a logit of `0.0` is kept at the default threshold.

## Classes

| class_id | Name | Species group |
| :--- | :--- | :--- |
| 0 | `RBB_FEMALE` | RBB |
| 1 | `RBB_MALE` | RBB |
| 2 | `WSB_FEMALE` | WSB |
| 3 | `WSB_MALE` | WSB |

Ship-gate metrics are species-grouped: classes 0 and 1 count as RBB, and classes 2 and 3 count as WSB. Sex classes are reported separately and are exposed only if each sex-class mAP50 meets the gate. r50-v5 meets it on test, but the app reports species only, as designed.

## Box conversion

Predicted boxes are normalised centre-width-height. Convert them to corner coordinates in original-image pixels, where `width` and `height` are the dimensions of the image after EXIF transposition:

```
x0 = (cx - w / 2) * width
y0 = (cy - h / 2) * height
x1 = (cx + w / 2) * width
y1 = (cy + h / 2) * height
```

Coordinates are returned as floats and are not clipped to the image bounds.

**Caller requirement.** `width` and `height` passed to `postprocess` MUST be the size of the EXIF-transposed image, that is `ImageOps.exif_transpose(img).size`. Do not use the raw `img.size`. On JPEGs that carry a rotation EXIF tag, the raw size is swapped relative to the image the model saw, so boxes come out wrong (transposed or misscaled) without any error.

## Output record

Each kept detection is a `Detection` dataclass (frozen):

| Field | Type | Meaning |
| :--- | :--- | :--- |
| `class_id` | int | Index into the Classes table |
| `score` | float | Max sigmoid probability over classes |
| `x0`, `y0`, `x1`, `y1` | float | Corner coordinates in original-image pixels |

## Reference implementation

- `src/rice_pest_detector/infer.py`: `preprocess(image, size=640)` and `postprocess(logits, boxes, width, height, threshold=0.5)`
- `tests/test_infer.py`: boundary and coordinate tests

## ONNX file SHA-256

Not listed here. The trained weights are published on [Kaggle](https://www.kaggle.com/models/kurtvalcorza/rice-pest-detector), one variation per model, each with a `manifest.json` that records the file's size and SHA-256. Each published model's manifest in this repository, `models/rice-pest-<id>.manifest.json`, also records its size and SHA-256.
