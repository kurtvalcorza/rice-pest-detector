---
title: "Rice-Pest Detector (RT-DETR → ONNX) — Design Spec"
date: 2026-10-13
status: approved design
owner: Kurt Valcorza
---


# Rice-Pest Detector — Design Spec

> **Note (18 Oct 2026).** This is the design as approved on 13 Oct 2026, kept as written. Since then r18vd missed the quality bar; the default model is r50-v5 (RT-DETR-r50vd, transformers 5.20.1), which meets the §6 model gates on test (count accuracy 0.849, species mAP50 0.943). Wave 2 (RF-DETR-M at 576 px, D-FINE-L) did not replace it, so the export input size is now set per model. The weights are published on Kaggle (Apache-2.0, dataset credited) rather than on Hugging Face or as a GitHub release. Current status: README, "Status and release gates".

> **Note (18 Oct 2026): edits for publication.** On 16 and 18 Oct 2026 this document was edited before the repository went public, without a note at the time. Names of organisations, of private repositories and of internal paths and files were removed or replaced with neutral wording (in the front matter, §1, §2, §4.6, §4.7, §5, §6, §7 and §9.2); the status line lost "implementation plan pending", and the §9.2 evidence location now points to the maintainers' records. No design decision, threshold or gate was changed.

## 1. Purpose

Produce an open, CPU-friendly object detector for rice black bug and white stemborer in light-trap
images, trained on open data, for use in the *Coding with AI Agents* workshop.
Secondary value: a reusable, honestly documented model.

**Interface for the tools that use it:** a published ONNX model with a pinned SHA-256, a model card,
sample test images, and a documented pre/postprocessing contract.

## 2. Decisions already made

| Item | Decision |
|---|---|
| Data | Full Deleña et al. light-trap rice pest dataset, Zenodo DOI 10.5281/zenodo.20066074, CC BY 4.0 |
| Detector | **RT-DETR**, Apache-2.0. Default backbone **`PekingU/rtdetr_r18vd`** (COCO-pretrained); fall back to `PekingU/rtdetr_r50vd` only if r18 misses the quality bar |
| Queries | 300 (trays with up to 106 insects occur in the data; DETR-R50's 100-query cap would undercount) |
| Training compute | **Colab T4** |
| Repo | `rice-pest-detector` (this repository) |
| Quality bar | §6 |

## 3. Source data (verified 2026-10-13)

- Extracted archive: 112,898 files, matching an earlier audit of the archive's inventory.
- Layout: `01_raw_images/`, `02_detection_dataset/{train,valid,test}/{images,labels}` (YOLO format), `03_roi_crops/`, `04_metadata/` (class dictionary, bounding boxes, split manifest, quality flags, acquisition metadata), `05_preprocessing_and_augmentation/`, `06_benchmark_tables/`, `08_scripts/`.
- Classes (`04_metadata/class_dictionary.csv`): `0 RBB_FEMALE`, `1 RBB_MALE`, `2 WSB_FEMALE`, `3 WSB_MALE` — rice black bug (*Scotinophara coarctata*), white stemborer (*Scirpophaga innotata*).
- Published split: train 6,760 images / **1,353** source-filename families; valid 169 / 169; test 169 / 168. The train split carries ~5 augmented variants per family; effective unique sources ≈ 1,690.
- **No pest-free images** in any split (0 empty label files). Test composition: 102 RBB-only, 34 WSB-only, 33 mixed.
- Label format: 652 label files contain YOLO-seg polygon rows (101 mixed with box rows); verified 2026-10-13.
- Known caveats (from an earlier audit of the dataset): capture date/location/trap fields blank in all 7,098 metadata rows; images pre-stretched to 640×640; annotations not documented as human-verified; one family crosses the published train/test split.

## 4. Pipeline

### 4.1 Data preparation (local, CPU)
1. Group images into **families** by the filename prefix before `_jpg.rf.`.
2. Validate every label: class id in 0–3, normalised box inside the image, positive area. Exclude a whole family if any member has an invalid box; log every exclusion with its reason. Polygon rows are converted to their min/max bounding box; other malformed rows exclude the family.
3. Near-duplicate screen (dHash) on one representative image per family (same rule as step 5); families within the measured threshold (see docs/evaluation-record.md) are merged into one group.
4. **Re-split by family group**, 70 / 15 / 15, stratified by species composition (RBB-only, WSB-only, mixed). Fixed seed.
5. Train keeps all variants of its families. Validation and test keep **one variant per family**: a family from the published valid/test splits uses its single image (Roboflow augments train only, so these are the only identifiable un-augmented originals; `05_preprocessing_and_augmentation/` carries no per-image flag). A family from the published train split uses its first **non-grayscale** variant by sorted filename (15% of augmentations are grayscale), else the first variant. The rule applied is recorded per image. Decided 2026-10-13: the 70/15/15 re-split stands even though most validation/test images are therefore augmented variants.
6. Outputs: `data/split_manifest.json` (per image: family, split, SHA-256, bytes, dimensions, source path inside the Zenodo archive) and COCO-format `annotations_{train,val,test}.json`. Images are never committed.
7. Test: assert no family or duplicate group appears in more than one split; assert manifest digests match the files.

### 4.2 Data into Colab
- Primary: single GET of the Zenodo archive (~1 GB, one request — avoids the range-request rate limiting that broke an earlier Colab run), verify archive MD5/SHA-256, extract only manifest paths, verify every image's SHA-256.
- Fallback: a private Google Drive copy of the same archive, verified the same way.
- Nothing is redistributed by this step.

### 4.3 Training (Colab T4)
- Hugging Face `transformers` `RTDetrForObjectDetection` from `PekingU/rtdetr_r18vd` at a pinned revision, new 4-class head, `num_queries=300`, input 640×640.
- fp16 mixed precision; batch size and learning rate set in the plan from a short smoke run; ~50–70 epochs.
- Checkpoint selection on **validation** species-grouped mAP50 only. The test split is not touched until §4.4.
- Checkpoint to Google Drive every epoch; resumable after a session drop.
- Reproducibility: pinned dependency lockfile, recorded seed, logged environment (GPU, driver, package versions).

### 4.4 Evaluation (held-out test, once)
- Species-grouped mAP50 (classes 0+1 → RBB, 2+3 → WSB), pycocotools.
- Per-image species **count accuracy**: share of test images whose predicted count per species, at the shipping confidence threshold, is within ±10% of the reference (an absolute ±1 tolerance applies when the reference count is below 10).
- Sex-level mAP50 per class; confusion matrix.
- Results recorded with the checkpoint hash.

### 4.5 Export
- ONNX, opset 17, fixed 640×640 input, static batch 1. Pre/postprocessing contract (resize, normalisation constants, box format, score semantics) written to `docs/inference-contract.md` — this is what every tool that runs the model implements.
- **Parity test:** on every test image, ONNX vs PyTorch detections above the shipping threshold match (same count and classes; box IoU ≥ 0.99; score difference ≤ 1e-3).
- Measure ONNX file size and median CPU latency with `onnxruntime` on a Windows laptop (record CPU model).

### 4.6 Model card
The model card: intended use (education, exploratory monitoring support), out-of-scope uses (agronomic decisions without expert review; species beyond the two classes), data caveats from §3, metrics from §4.4 including any that miss the bar, licences (model Apache-2.0; data CC BY 4.0 with full attribution), and the training environment.

### 4.7 Handoff to the tools that use it
- Sample images from the test split, under CC BY 4.0 attribution.
- Recorded model outputs on those images, so tests can run without the model.
- ONNX SHA-256 and download location.

## 5. Repository layout (outline; the plan fixes exact files)

`src/rice_pest_detector/` (data prep, metrics, export, inference contract), `notebooks/train_colab.ipynb`
(generated, not hand-edited), `tests/` (CPU-only), `data/` (manifests and annotations only),
`docs/` (specs, inference contract, evaluation record), the model card, `LICENSE` (Apache-2.0).

## 6. Quality bar (ship gate)

| Gate | Threshold |
|---|---|
| Species-grouped mAP50 (test) | **≥ 0.80** |
| Count accuracy (test) | per-species count within ±10% on **≥ 80%** of images. Always reported beside the no-detection baseline (≈46% on test, from the ±1 tolerance below 10), per-species MAE, signed bias, exact-count rate and presence recall (owner decision 2026-10-14) |
| Sex-level classes exposed to students | only if each sex class mAP50 **≥ 0.70**; otherwise the app reports species only |
| ONNX size | ≤ 200 MB |
| CPU latency | ≤ 5 s/image median on the reference Windows laptop |
| Parity | §4.5 test passes on every test image |

If r18vd misses a quality gate, retrain with r50vd once. If r50vd also misses, stop and report — the
project owner decides whether to ship with documented limits.

## 7. Out of scope
Pest-free image synthesis; additional species; ROI-crop classifiers; production deployment; publishing
(gated, §8).

## 8. Owner gates
- **Publishing weights** (outward, irreversible once indexed): needs explicit approval and the hosting choice (Hugging Face model repo vs GitHub release).
- Shipping below the quality bar (§6).

## 9. Verification
1. CPU test suite passes (split integrity, manifest digests, metrics on synthetic fixtures, parity on a tiny fixture).
2. Recorded Colab T4 run: notebook source matches the repo head; execution log and metrics kept in the maintainers' records; their SHA-256 values are in `docs/evaluation-record.md`.
3. §6 gates evaluated and recorded with the checkpoint hash — each result labelled built / CPU-tested / hosted-executed / human-reviewed, none implying the next.
