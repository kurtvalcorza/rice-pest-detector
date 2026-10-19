# Contract: inference, as the app implements it

The project's contract is `docs/inference-contract.md`, with `src/rice_pest_detector/infer.py` as the reference. This file maps each step to the Dart code that implements it and the test that holds it there. Constants are in `app/lib/inference/contract.dart`; `contract_test.dart` checks them against the Python package.

## Steps

| # | Step | Rule | Dart | Test |
| :-- | :-- | :-- | :-- | :-- |
| 1 | Decode | Read the file; JPEG decoder applies the EXIF tag; other formats are rotated with `applyExifOrientation`; unreadable bytes throw `PhotoUnreadable` | `decode.dart` `decodePhoto` | `decode_test.dart` (tags 1–8 against Pillow) |
| 2 | Colour | Grey, RGBA and palette images become 8-bit RGB | `decode.dart` | `decode_test.dart` |
| 3 | Size check | Each side at least 32 px, else `PhotoTooSmall` | `preprocess.dart` `minSide` | `contract_test.dart` |
| 4 | Resize | Pillow `BILINEAR` to S × S, S = the manifest's `input_size` (640 default, 576 for RF-DETR-M); aspect ratio not kept; no letterbox | `preprocess.dart` `resizeBilinear` | `contract_test.dart`: byte-identical at 640 (8 shapes) and 576 (7 shapes) |
| 5 | Tensor | ÷ 255, no mean or std; NCHW float32 `(1, 3, S, S)`, input name `pixel_values` | `preprocess.dart` `toTensor`, `onnx_detector.dart` | `contract_test.dart` |
| 6 | Run | ONNX Runtime 1.28.0 through `flutter_onnxruntime`; outputs `logits` and `pred_boxes`, each 1 × 300 × 4 | `onnx_detector.dart` `OnnxDetector` | None on device (R8); shapes enforced at import by `model_check.dart` |
| 7 | Score | Sigmoid in double precision, max over the 4 classes, class = argmax | `postprocess.dart` | `contract_test.dart`: 3 reference cases |
| 8 | Floor | The detector keeps scores `>= 0.02` (`detectorFloor`) | `onnx_detector.dart` `minScore` | `onnx_detector_floor_test.dart` |
| 9 | Boxes | `x0 = (cx − w/2)·W` etc., W and H the upright image size; not clipped | `postprocess.dart` | `contract_test.dart` |
| 10 | Sort | By score, descending; ties in query order; no NMS | `postprocess.dart` | `contract_test.dart` |
| 11 | Count | Keep `score >= threshold` (inclusive, the manifest's `threshold`); count per species: classes 0–1 → RBB, 2–3 → WSB | `counting.dart` `countPhoto` | `counting_test.dart` |
| 12 | Review flags | `lowConfidence` if any counted score `< review_below`; `crowded` if more than 30 counted | `counting.dart` | `counting_test.dart` |

## Golden fixtures

| File | Generator | Contents |
| :-- | :-- | :-- |
| `app/test/fixtures/contract_fixtures.json` | `tools/export_app_fixtures.py` | Contract constants; orientation cases 1–8 (5 × 3 pattern); resize at 640 for 37×23, 1000×700, 640×640, 1080×1920, 4032×3024, 3024×4032, 4000×1000, 1000×4000 (SHA-256 of the resized bytes plus 8 sample pixels); 3 post-processing cases (square, landscape, portrait) including a logit of exactly 0 (score 0.5, kept at 0.5) |
| `app/test/fixtures/resize_fixtures.json` | `app/tool/export_resize_fixtures.py` | Resize at 576 for 37×23, 1000×700, 576×576, 640×640, 1080×1920, 4032×3024, 4000×1000 |

Both use the pattern `(x*7 + y*13 + c*101 + (x*y) % 31) % 256`; no photos are stored. Both have `--check`, run in CI. Regenerate both after any contract change, in the same change as the reference and the Dart code (Principle II).

## Known difference

JPEG decoding is not byte-identical to Pillow's (a level or two per pixel), so on real photos parity is at the level of kept detections, not pixels. It is recorded here and in `decode.dart`; it has not been measured on real photos on a phone.
