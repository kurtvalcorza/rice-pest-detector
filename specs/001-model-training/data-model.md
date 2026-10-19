# Data Model: Rice-Pest Model Training

**Feature**: [spec.md](spec.md) | **Plan**: [plan.md](plan.md)

All data is files. Committed files are marked **(git)**; run files live in `runs/<run folder>/` or the matching Drive folder and are not tracked. The formats of the files other projects read are fixed in [contracts/](contracts/).

## Family and duplicate group (in `data/split_manifest.json`)

| Field | Type | Rule |
| :-- | :-- | :-- |
| `family` | string | Lower-cased file-name stem before `_jpg.rf.` / `_png.rf.` (`families.family_key`); a non-Roboflow name is an error |
| `group` | string | `grpNNNNN`; families whose representatives are within dHash distance 1 share a group |

A family belongs to exactly one group, and a group to exactly one split. 1,684 families, 1,600 groups (1,122 / 239 / 239).

## Image record (git: `data/split_manifest.json`)

| Field | Type | Rule |
| :-- | :-- | :-- |
| `file` | string | File name in the dataset |
| `relative_path`, `archive_member` | string | Path under the dataset folder, and the same path with the `datasets/` prefix used inside the archive |
| `family`, `group` | string | As above |
| `split` | `"train"`, `"val"` or `"test"` | From the group |
| `origin_split` | `"train"`, `"valid"` or `"test"` | The dataset's published split |
| `selection_rule` | `null`, `"published-original"`, `"first-colour"` or `"first-any"` | `null` in train; the rule that picked the one image in val and test |
| `sha256`, `bytes` | string, int | Checked when the image is extracted |
| `width`, `height` | int | 640 × 640 for every image |
| `boxes` | list of `[class_id, cx, cy, w, h]` | Normalised YOLO boxes; polygons already converted; at most 300 per image |

Top level: `{"seed": 20261013, "images": [...]}`. Full format: [contracts/split-manifest.md](contracts/split-manifest.md).

## Exclusion (git: `data/exclusions.json`)

`{"family", "reason"}`. One today: family `img_2002`, missing label.

## Annotation set (git: `data/annotations_{train,val,test}.json`)

COCO detection format: `images` (`id` from 1, in manifest order, `file_name`, `width`, `height`), `annotations` (`bbox` in pixels `[x, y, w, h]`, `category_id` 1–4, `area`, `iscrowd: 0`), `categories` (`RBB_FEMALE`, `RBB_MALE`, `WSB_FEMALE`, `WSB_MALE`). The evaluator asserts that image `i` of the annotation file is record `i` of the split.

## Training configuration and experiment (run: `config.json`)

`TrainConfig`: `base_model`, `revision`, `epochs` (60; 40 for every run after r18-1), `batch_size` (8; 4 after r18-1), `lr` 1e-4, `backbone_lr` 1e-5, `weight_decay` 1e-4, `grad_clip` 0.1, `seed` 20261013, `num_queries` 300, `fp16` true, `num_workers` 2, `input_size` 640 (576 for RF-DETR-M).

**Experiment fingerprint**: the configuration without `num_workers` (and without `input_size` when it is 640), the SHA-256 of the split manifest and the SHA-256 of the validation annotations. Resume compares it and refuses a mismatch.

## Checkpoints (run: `last.pt`, `best.pt`, `best.json`)

| File | Holds | Written |
| :-- | :-- | :-- |
| `last.pt` | weights, optimiser, scheduler, scaler, epoch, best metric, experiment, random state | Every epoch, atomically (`.tmp` then rename) |
| `best.pt` | weights, `map50_species`, epoch, experiment | When validation species mAP50 improves, atomically |
| `best.json` | `map50_species`, epoch | After `best.pt`; a readable copy that resume does not trust |

## History row (run: `history.jsonl`)

One line per epoch: `epoch`, `train_loss`, `updates`, `nonfinite_loss_steps`, `skipped_updates`, `grad_scale`, then the evaluation result on validation at threshold 0.5. A truncated last line is dropped with a warning; rows from the resume epoch onwards are trimmed before training continues.

## Evaluation result (run: `test_metrics.json`; history rows)

`map50_species`, `map50_by_class`, `threshold`, `count_accuracy`, `count_accuracy_no_detection_baseline`, `count_errors` (per species: `mae`, `bias`, `exact`, `presence_recall`, `mae_by_density`), `detections_kept`, `top_score_per_image` (p50, p90, max), `confusion`. A test result adds `best_pt_sha256`, `epoch` and `evaluation` (the identity below). Full rules: [contracts/evaluation-reporting.md](contracts/evaluation-reporting.md).

**Evaluation identity**: `best_pt_sha256`, `manifest_sha256`, `annotations_sha256`, `threshold`, `evaluator_version` (2). A cached result is refused when any of them differs.

## Threshold and calibration reports (run: `demo_threshold.json`, `calibration_val.json`, `val_dets_onnx.json`)

Validation only. The threshold report holds the sweep (threshold, total MAE, count accuracy, count errors, detections kept) and the chosen threshold. The calibration report holds the Platt `a`, `b`, the calibrated and count-optimal thresholds, calibration error raw / in-sample / out-of-fold, and in-sample and out-of-fold count reports per fold (5 folds, seed 20261016). The detection cache is reused only when the ONNX file's SHA-256 matches.

## Exported model and export record (run: `models/<name>.onnx`, `models/<name>.json`)

ONNX opset 17, input `pixel_values (1, 3, S, S)`, outputs `logits (1, 300, 4)` and `pred_boxes (1, 300, 4)`. The export record holds `sha256`, `bytes`, `opset`, `input`, `outputs`, `checkpoint_sha256`, `checkpoint_epoch`. Neither file is committed.

## Model manifest (git: `models/rice-pest-<id>.manifest.json`)

The strict description of a published model, copied verbatim into the app's catalogue. Fields and rules: [contracts/model-manifest.md](contracts/model-manifest.md).

| id | input_size | threshold | review_below | bytes | validation count accuracy |
| :-- | --: | --: | --: | --: | --: |
| `r50-v5` (default) | 640 | 0.48 | 0.64 | 171,744,970 | 0.834 |
| `rfdetr-m` | 576 | 0.48 | 0.63 | 121,956,743 | 0.846 |
| `dfine-l` | 640 | 0.50 | 0.68 | 125,213,572 | 0.822 |

## States

**Model lifecycle**: `trained` (best.pt chosen on validation) → `exported` (ONNX + record) → `judged on validation` (threshold, calibration, rules A, B, D) → `tested` (only under rule C) → `published` (manifest + card + Kaggle variation). A model can stop at any state; r18-1 and r50-1 stopped before `published`.

**Test-split budget**: `unused` → `looked once` (r18-1, 13 Oct, threshold 0.5) → `looked twice` (r50-v5, 18 Oct, threshold 0.48, rule C) → `spent`. The post-hoc challenger evaluations of 18 Oct do not move the state; they are recorded as comparison only. A later model needs a new held-out set.
