# Contract: model manifest (and the export record it is built from)

Each published model has one manifest, `models/rice-pest-<id>.manifest.json`, the only files under `models/` that git tracks (`.gitignore`: `models/*`, `!models/*.manifest.json`). The same JSON is published next to the model on Kaggle as `manifest.json` and copied verbatim into the app's catalogue, `app/assets/model_catalog.json`. The app's parser (`app/lib/model/model_manifest.dart`, `ModelManifest.fromJson`) is the enforcing implementation.

## Fields

| Field | Type | Rule |
| :-- | :-- | :-- |
| `id` | string | 1–64 characters: lower-case letters, digits, `.`, `_`, `-`, starting with a letter or digit |
| `label` | string | Not empty |
| `architecture` | string | For example `"RT-DETR (ResNet-50)"` |
| `base_model` | string | Hugging Face id of the base model, for example `"PekingU/rtdetr_r50vd"` |
| `licence` | string | `"Apache-2.0"` for all three |
| `input_size` | int | 320–1280; the side of the square input (contract `size`) |
| `threshold` | number | Strictly between 0 and 1, above the app's detector floor (0.02); the counting threshold chosen on validation |
| `review_below` | number | Strictly between 0 and 1 and not under `threshold`; a photo is flagged when a counted detection scores below it (for r50-v5, raw 0.64 calibrates to 0.74 on validation) |
| `sha256` | string | 64 lower-case hex digits, of the `.onnx` file |
| `bytes` | int | Positive; size of the `.onnx` file |
| `outputs` | list | Exactly `["logits", "pred_boxes"]` |
| `num_classes` | int | Exactly 4 |
| `validation` | object | Exactly `count_accuracy` (out-of-fold, 0–1), `species_map50` (0–1), `wsb30_mae` (≥ 0, the 18 dense validation trays) |
| `validated` | bool | `false` for every model: none is validated in the field |
| `notes` | string | Optional; the only optional field |

Unknown or missing fields are rejected, at the top level and inside `validation` (constitution, Principle VI).

## Current manifests

| `id` | `threshold` | `review_below` | `input_size` | `sha256` (start) | `notes` |
| :-- | --: | --: | --: | :-- | :-- |
| `r50-v5` | 0.48 | 0.64 | 640 | `dc3927ae` | none |
| `rfdetr-m` | 0.48 | 0.63 | 576 | `07161f11` | none |
| `dfine-l` | 0.50 | 0.68 | 640 | `c823f5d8` | the parity score waiver |

The default model is r50-v5, identified in the app by its SHA-256 and in `app/assets/model_pin.json` (`"kind": "demo"`, threshold 0.48, the Kaggle version 3 URL).

## Where the values come from

| Field | Source |
| :-- | :-- |
| `sha256`, `bytes` | The export record, `models/<name>.json`, written by `tools/export_onnx.py` (`sha256`, `bytes`, `opset`, `input`, `outputs`, `checkpoint_sha256`, `checkpoint_epoch`; not committed) |
| `input_size` | The `--size` passed to the export, equal to the training `input_size` |
| `threshold` | `tools/choose_demo_threshold.py` and the out-of-fold folds of `tools/calibrate_scores.py`, on validation |
| `review_below` | The Platt fit from `tools/calibrate_scores.py` on validation |
| `validation.*` | `docs/evaluation-record.md`, "Wave 2" (out-of-fold count accuracy, best-epoch species mAP50, WSB 30+ MAE) |

The manifest itself is written by hand from these sources; no tool generates it.

## Checks

- `app/test/published_models_test.dart`: the catalogue lists r50-v5, rfdetr-m and dfine-l with https URLs; r50-v5 is the default; each catalogue manifest equals the file in `models/`.
- The app's download and import checks: a model is used only when the file's size and SHA-256 match, its input and output names and shapes match the contract and a synthetic-photo self-test gives finite outputs ([002-mobile-app](../../002-mobile-app/spec.md)).

## Change rule

A manifest describes one file, by its SHA-256 and size. Changing the files of a published model means a new Kaggle version, which would change the app's pinned download URL; the decision log keeps each variation at version 3 for that reason (`docs/decisions.md`, 18 Oct).
