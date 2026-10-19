# Evaluation record

## Data preparation

Date: 2026-10-13. Command: `python -m rice_pest_detector.manifest --dataset-root <riceprotek-insects-v28/datasets> --out data`. YOLO-seg polygon label rows are converted to min/max boxes.

### Near-duplicate threshold (diagnostic)

dHash on one representative per family (published valid/test original, else first non-grayscale variant, else first), 1,684 families:

| Hashed images | max_distance | Groups | Largest group (families) | Largest % | Multi-family groups |
| :-- | --: | --: | --: | --: | --: |
| representatives | 0 | 1,676 | 3 | 0.18% | 7 |
| representatives | 1 | 1,600 | 21 | 1.25% | 37 |
| representatives | 2 | 1,330 | 281 | 16.69% | 42 |
| representatives | 3 | 1,105 | 563 | 33.43% | 17 |
| representatives | 4 | 978 | 699 | 41.51% | 8 |
| all variants (first attempt) | 4 | 905 | 779 | 46.26% | 2 |

Rule: the largest d whose largest group holds at most 2% of families. Chosen **DEDUP_MAX_DISTANCE = 1**. Hashing all variants at d=4 chained 779 families into one group, which the split sent to val (634/914/136 families).

### Cross-split nearest-neighbour check (diagnostic)

The dedup rule fixes d=1 so that no group exceeds 2% of families; it does not claim that families at larger distances are different scenes. `tools/nn_leakage_check.py` reports, for each val/test family, the Hamming distance from its representative to the nearest train representative (same representative rule as the split):

```
python -m tools.nn_leakage_check --dataset-root <riceprotek-insects-v28/datasets>
```

| Split | Families | Min distance | Within d<=2 | Within d<=4 |
| :-- | --: | --: | --: | --: |
| val | 253 | 2 | 51 | 106 |
| test | 252 | 2 | 42 | 103 |

Manual inspection of the close pairs: all inspected pairs were single-insect photos with different IMG numbers, pixel correlation 0.74-0.97. Three test pairs above 0.95 are still to be inspected by eye: `img_2657` / `img_1918`, `img_2427` / `img_2267`, `img_2569` / `img_2308`.

The 2% rule protects the split; it is not a definition of a duplicate.

### Reporting note for later gates

Count accuracy will also be reported split by reference count (1 vs 5 or more). About 46% of val/test images contain exactly one insect, so a pooled count accuracy overstates counting skill on crowded scenes.

### Result

```json
{"images": {"train": 4948, "val": 253, "test": 252}, "families": 1684, "groups": 1600, "excluded_families": 1}
```

Checks (script over `data/split_manifest.json`):
- Families per split: train 1,179 / val 253 / test 252 (70.0 / 15.0 / 15.0%). Groups: 1,122 / 239 / 239.
- Leakage: 0 families and 0 groups appear in more than one split.
- Exclusions: 1 family, `img_2002` (missing label). No malformed-row exclusions.
- Eval selection rule: val 56 published-original + 197 first-colour; test 38 + 214.
- Images with polygon-derived boxes: 516 of 5,453 manifest images (12,149 polygon rows).
- Build environment: Pillow 12.3.0, numpy 2.5.4 (venv used to build `data/`; dHash and the image-grey test depend on them).
- JSON size: 19.4 MB total (split_manifest 9.6 MB, annotations_train 9.0 MB, val 0.4 MB, test 0.5 MB).

## Training module

- Base checkpoint: `PekingU/rtdetr_r18vd` pinned at revision `ac77a11ff0170a41b771c03264987f8ce2b0d753` (resolved 2026-10-13 via HfApi.model_info).
- Environment for module tests and CPU smoke run: torch 2.14.1+cpu, transformers 4.57.6, scipy 1.18.1 (required by `RTDetrHungarianMatcher`; added to the `train` extra).
- Tests: `pytest tests/test_train.py -m torch` passes (collate; checkpoint round trip restores epoch, best metric, optimiser and scheduler state under `torch.load(weights_only=True)`).
- CPU smoke run (8 train images, 4 val images, 1 epoch, batch 2, fp16 off): completed; `history.jsonl` has 1 line, `last.pt` and `best.pt` written to `runs/smoke/` (gitignored). Val mAP50 on 4 images was 0.0025 after one epoch, which is noise; only completion is claimed. Not a training result.

## Colab data path

Evidence for the archive layout and digest, checked 2026-10-13:

- **Member prefix (`datasets/`).** An earlier audit of the archive lists 200 records whose `zip_member.name` values are real archive members, for example `datasets/02_detection_dataset/train/images/IMG_1187_JPG.rf.38552e3f914b5b17b7d012228e5380c6.jpg`. That file was built from the real archive with CRC checks, so the `datasets/` prefix in `archive_member` is consistent with the archive.
- **Archive SHA-256.** An earlier audit of the dataset records `f4a0409977e0615e34f3cf2b936a5ca9dd3a91b153d239e314334ea40c2537f7` for the 1,005,857,218-byte archive, measured 2026-09-28 on a local copy whose size and MD5 matched Zenodo. This is the value in `ZENODO_SHA256`.
- **Zenodo record.** `https://zenodo.org/api/records/20066074` (fetched 2026-10-13, 4.7 KB JSON; the archive was not downloaded) lists one file, `datasets.zip`, with `md5:24960c245a3a21b63be95314cc7467da`. It gives no member names and no SHA-256, so it corroborates size and MD5 only.

Final end-to-end check: the first Colab run is the last verification of the prefix and digests together.

Contingency: if the first run raises `KeyError` naming a member, `extract_members` has found the member missing. Correct the `archive_member` prefix in `manifest.py`, regenerate `data/` and update this section with the observed layout.

## Colab run instructions

1. In a browser, open colab.research.google.com, File > Upload notebook, pick `notebooks/train_colab.ipynb`, set Runtime > Change runtime type to T4 GPU, then Run all and accept the Drive consent popup. Use the browser, not an editor connected to a Colab runtime: on 2026-10-13 `drive.mount` failed from an editor with `credential-propagation:enable failed, reason: read ECONNRESET`.
2. If the Zenodo download fails, copy the local `datasets.zip` to Drive `rice-pest-detector/datasets.zip` and Run all again. The notebook prefers that copy and verifies it against the same size, MD5 and SHA-256 pins.
3. After a disconnect, Run all again; training resumes from the last checkpoint on Drive.
4. Check Drive Trash after epoch 2: overwritten checkpoints may land in Trash and count against quota. Empty it if free space falls under 20 GB (the drive cell prints free space at start and warns below 20 GB).
5. Wait for Drive sync to finish before closing the session.
6. When finished: File > Download > .ipynb, and copy `best.pt`, `history.jsonl`, `test_metrics.json` and the `env-<UTC timestamp>.txt` log from Drive `rice-pest-detector/run-r18/` to the local repo's `runs/run-r18/` (gitignored).
7. The agent then keeps the executed notebook in the maintainers' records (not in this repository), confirms its source matches the committed notebook, and records `test_metrics.json` and the `best.pt` SHA-256 here, labelled **hosted-executed**.

## Run r18-1 (2026-10-13), hosted-executed

Evidence: the executed notebook `train_colab.executed.ipynb`, kept in the maintainers' records and not distributed with this repository (SHA-256 `44c0c5d98345ef81200670ff0e7d67bbf2ab58a63fc75f4b011a170e7dd34a86`). Its 24 cell sources match the committed `notebooks/train_colab.ipynb` of that run, ignoring the `# @title` lines Colab added.

- Runtime: **NVIDIA A100-SXM4-40GB**, not the planned T4. Python 3.13.15, torch 2.11.0+cu130, transformers 4.57.6.
- The export is a later session: the fit cell printed `resumed at epoch 60, best val mAP50 0.8287`, and the test cell printed an existing `test_metrics.json`. Training and the test evaluation ran in earlier sessions whose outputs are not in this file.
- Selected checkpoint: **epoch 3 of 60**, `best.pt` SHA-256 `d970154fe242143813ef453afbe0a12a702258b3197fcf620e2922569185afa3`.
- The test split has been evaluated once, on this checkpoint.

| Test metric (threshold 0.5) | Value | Gate |
| :-- | --: | :-- |
| Species-grouped mAP50 | 0.835 | >= 0.80: met |
| Four-class mAP50 | 0.720 (RBB_F 0.852, RBB_M 0.638, WSB_F 0.618, WSB_M 0.770) | each sex class >= 0.70: not met (2 of 4 below) |
| Count accuracy | 0.456 | >= 0.80: **not met** |
| Detections kept at 0.5 | **0** (confusion lists all 3,320 test insects as missed) | |

**Finding: the model keeps no detections at the 0.5 threshold.** mAP is computed from all detections (threshold 0.0) and only needs correct ranking, so it is unaffected; counts and confusion use detections scoring >= 0.5. Count accuracy 0.456 equals the no-detection baseline exactly (115/252, recomputed 2026-10-14 with `metrics.count_accuracy` on all-zero predictions; val baseline 0.474). `infer.postprocess` scores are standard (sigmoid, max over classes), so the scores themselves are low. Likely contributors, not yet confirmed: an early (epoch 3) checkpoint whose scores are still low, and whatever kept validation mAP from improving after epoch 3. Diagnosis needs `history.jsonl` and `best.pt` from Drive.

Not yet known: the training curve, the validation score distribution and a validation-chosen threshold. Any threshold change is chosen on validation only; the test result above stays the recorded one.

## Review fixes (2026-10-14)

An external review of the notebook (2026-10-14) was triaged with the owner. Built and CPU-tested (86 tests pass); not yet hosted-executed.

- **fp16 matching.** `build_model` wraps the model's loss so the Hungarian matcher and all losses (final, auxiliary, encoder) run in float32 with autocast off. In float16 the matcher's `log(p + 1e-8)` can produce inf costs that scipy rejects before the finite-loss check runs. CPU torch cannot run the matcher in half precision, so the test pins the contract: under autocast every tensor reaching the loss is float32.
- **Skipped updates.** An update is skipped when the clipped gradient norm is non-finite. History rows now log `updates`, `skipped_updates`, `nonfinite_loss_steps` and `grad_scale`.
- **Best checkpoint.** `best.pt` now holds weights, score, epoch and experiment fingerprint in one atomic file; `best.json` is a readable copy only. `load_best` still reads the r18-1 bare state_dict.
- **Resume identity.** `last.pt` stores an experiment fingerprint (config except `num_workers`, manifest hash, val annotations hash). A mismatch stops with the changed fields and asks for a new `RUN_DIR`. Python, NumPy, torch and CUDA RNG state are restored on resume.
- **History.** A truncated final `history.jsonl` line is dropped with a warning; corruption anywhere else still raises.
- **Cached test result.** `test_metrics.json` records the full evaluation identity (best.pt, manifest, annotations, threshold, evaluator version) and `check_cached_test` refuses any mismatch. The r18-1 record predates this and is checked on the weights hash only.
- **Count metrics.** Per the owner (2026-10-14), the count-accuracy gate stays at >= 80% but is always reported beside the no-detection baseline, per-species MAE, signed bias, exact-count rate, presence recall and MAE by density (1-9, 10-29, 30+). `evaluate` also reports detections kept and per-image top-score quantiles.
- **Labels.** NaN and inf coordinates are rejected.
- **GPU.** The notebook stops at the versions cell if no GPU is attached.
- **EXIF.** Scanned all 5,453 manifest images in the local archive copy: every image is 640x640, none has a rotation tag, all sizes match the manifest. No issue.
- **Line endings.** `.gitattributes` forces LF for `data/*.json`; with `core.autocrlf=true` they had been checked out as CRLF, which made `build_notebook.py --check` fail on this machine.

Deferred to the model card: the holdout is a family-grouped re-split (most val/test images are first-colour export variants, 197/253 and 214/252), there are no pest-free images, and no field-readiness claim is made.
## Base vs fine-tuned (2026-10-16), validation only

Question: how much did fine-tuning add over the starting checkpoint? `PekingU/rtdetr_r18vd` is COCO-pretrained and COCO has no rice-pest classes, so the base model cannot be scored as-is. "Base" here is the pinned checkpoint with the freshly initialised 4-class head, which is the model at the start of training. The head is random, so it was scored under three seeds (20261013 = training seed, 1, 2). Both models go through `train.evaluate` (evaluator v2) on the 253 validation images; the test split was not read.

Command: `python -m tools.compare_base_vs_finetuned --best runs/run-r18/best.pt --image-root <riceprotek-insects-v28>/datasets --out runs/run-r18/base_vs_finetuned_val.json` (CPU). Check: the fine-tuned species mAP50 (0.829) and four-class values reproduce the training log's epoch-3 row exactly.

| Validation metric | Base, untrained head (3 seeds) | Fine-tuned r18-1 (best.pt) |
| :-- | --: | --: |
| Species-grouped mAP50 | 0.001-0.007 | **0.829** |
| Four-class mAP50 | 0.001-0.003 | **0.704** |
| RBB_FEMALE / RBB_MALE | <= 0.008 / <= 0.004 | 0.850 / 0.667 |
| WSB_FEMALE / WSB_MALE | 0.000 / <= 0.001 | 0.519 / 0.780 |
| Count accuracy at 0.5 (baseline 0.474) | 0.004-0.423 | 0.474 (0 detections kept) |
| Count accuracy at 0.04 demo threshold | 0.000 (all 300 queries kept per image) | **0.632** |
| Count MAE at 0.04, RBB / WSB | 111-246 / 44-178 | **1.09 / 2.75** |
| Per-image top score, max | 0.71-0.82 | 0.25 |

Reading:

- **Fine-tuning is where all detection skill comes from.** The base model's mAP50 is effectively zero; the fine-tuned model reaches 0.829 (species) and 0.704 (four classes). Most of that arrives in the first epoch (0.728 species mAP50 after epoch 0 in `history.jsonl`), peaks at epoch 3 (0.829), then plateaus near 0.80 for the remaining 56 epochs.
- **The untrained head is not "low-scoring"; it is randomly confident.** Its top scores reach 0.71-0.82, so at 0.5 it keeps hundreds to thousands of wrong boxes, and its count accuracy swings with the seed (0.004-0.423), always at or below the do-nothing baseline. Fine-tuning taught the model *where* insects are (high mAP) but pushed every score below 0.25. The low scores are produced by training, which supports the calibration diagnosis rather than an undertrained head.
- **Counts at the demo threshold** (chosen on this same split, so optimistic): fine-tuned MAE is about 1 insect per image for rice black bug and about 3 for white stemborer, worsening with density (WSB 30+ per image: MAE 15.8). Both species are found on 97-99% of the images where they occur (presence recall).

### Outside reference: the dataset's own detector benchmark

The dataset ships detector results (`06_benchmark_tables/yolo/yolo_comparison_outputs/`): YOLO11s, YOLO12s and YOLO26s, 20 epochs, four-class mAP50 **0.860-0.872** on the authors' validation split (per class: RBB_F 0.93-0.95, RBB_M 0.90-0.93, WSB_F 0.69-0.72, WSB_M 0.90-0.91). This is a reference, not a like-for-like comparison: the authors' split is not our family-grouped, near-duplicate-free split, which removes export variants of the same tray from the holdout and is expected to score lower. Two things transfer anyway. WSB_FEMALE is the weakest class in every model, theirs and ours. And r18-1's four-class 0.704 sits well below their 0.86-0.87, so a larger backbone (r50) or YOLO-class baseline on our split is worth a run before concluding RT-DETR-r18 is the right model. The `transformer/` tables (Swin-T 0.918, ViT-B/16 0.897 accuracy) are single-insect crop classifiers, not detectors, and are not comparable.

## Score calibration (2026-10-16), validation only

Owner decision (2026-10-16): calibrate r18-1 before retraining. `tools/calibrate_scores.py` runs the exported ONNX model (`models/rice-pest-r18-1.onnx`, sha 8ffc7841…) on the 253 validation images and keeps detections scoring >= 0.01. Each detection is labelled true if it claims an unclaimed same-species truth box at IoU >= 0.5 (greedy, score order). The tool then fits Platt scaling, p = sigmoid(a * logit(score) + b). Calibration is monotone, so in the app it is exactly a threshold change: no code change, no contract change. To keep the estimate honest, every count result is also reported out-of-fold: 5 folds with images grouped by family, as the splits are, and the count-optimal (MAE) threshold re-chosen inside the same folds. The test split was not read.

Command: `python -m tools.calibrate_scores --onnx models/rice-pest-r18-1.onnx --dataset-root <riceprotek-insects-v28> --out runs/run-r18/calibration_val.json --cache runs/run-r18/val_dets_onnx.json`.

Fit: a = 4.15, b = 12.63 on 24,831 detections (2,837 true; 2,913 truth insects). A calibrated probability of 0.5 corresponds to **raw score 0.046**. Per-fold refits give a 3.96-4.32 and a raw threshold of 0.044-0.048, so the fit is stable. Expected calibration error falls from 0.092 (raw scores) to 0.019 (out-of-fold). Observed precision by raw score: 0.3% at 0.01-0.02, 14% at 0.02-0.04, 65% at 0.04-0.06, 81% at 0.06-0.10, 94% at 0.10-0.15.

| Validation counting rule | Count accuracy (gate 0.80) | MAE RBB / WSB | Bias RBB / WSB | WSB MAE, 30+ per image |
| :-- | --: | --: | --: | --: |
| No detections (baseline) | 0.474 | 4.77 / 6.75 | -4.77 / -6.75 | 44.4 |
| Specified threshold 0.5 | 0.474 | 4.77 / 6.75 | -4.77 / -6.75 | 44.4 |
| Calibrated p >= 0.5 (raw 0.046), out-of-fold | 0.597 | 1.36 / 2.87 | -0.84 / -0.53 | 17.9 |
| Count-optimal threshold (raw 0.04), out-of-fold | **0.632** | 1.09 / 2.75 | -0.45 / +0.87 | 15.8 |
| Expected count (sum of calibrated p), out-of-fold | 0.549 | 1.40 / 2.72 | -0.67 / +0.22 | 15.7 |

Reading:

- **Calibration fixes what the scores mean, not how well the model counts.** After calibration a score is an honest probability, and the 0.5 rule keeps detections again. But every counting rule tops out at 0.60-0.63 count accuracy on validation, well short of the 0.80 gate.
- **The 0.04 demo threshold holds up out-of-fold.** It was re-chosen as 0.04 in all 5 folds, so its out-of-fold result equals the in-sample one (0.632). Its sitting just below the calibrated 0.046 is consistent: counting is best when a few doubtful detections are kept.
- **Density is the remaining failure.** White stemborer trays with 30+ insects are miscounted by about 16-18 per image under every rule. That is a detection-recall limit, which calibration cannot move.
- **Solver note.** Plain Newton oscillated and overflowed on these scores (a = -7.6e7 on the first run). The fit now halves each step until the penalised likelihood improves, and a regression test runs on the cached real detections.

**Test split not run.** This step was planned with a second test look, which needs an explicit owner exception; none was requested, because the best validation result (0.632) is already below the 0.80 gate: a test run could only confirm a failure and would spend the holdout's second and last look. Recommended next step: retrain (r50 backbone, or a YOLO baseline on this split for comparison) aimed at dense-tray recall, then calibrate the new model on validation and spend the test look on that. For the app's demo mode, either 0.04 or the calibrated 0.046 is defensible; 0.04 stays, as it counts best.


## Figures used in the teaching decks (2026-10-16)

The HTML decks in `docs/presentations/` quote figures that were computed from run files but not yet written here. They are recorded now, generated from the files named, so every deck number has a source. Dataset facts on the decks (6,760 published training images, 1,353 families, 0 pest-free images, 0 of 7,098 metadata rows with capture date, place or trap, trays of up to 106 insects) come from the dataset facts checked on 2026-10-13, now recorded in `specs/001-model-training/research.md`, R0.

**Training curve** (`runs/run-r18/history.jsonl`, 60 rows, epochs numbered from 0). Training loss 10.40 at epoch 0 to 3.39 at epoch 59. Validation count accuracy at threshold 0.5 took one value in all 60 epochs: 0.4743 (the no-detection baseline). Validation species mAP50 by epoch: 0.728, 0.687, 0.795, 0.829, 0.772, 0.786, 0.690, 0.775, 0.803, 0.796, 0.761, 0.752, 0.785, 0.782, 0.779, 0.709, 0.702, 0.785, 0.814, 0.806, 0.786, 0.796, 0.811, 0.738, 0.804, 0.732, 0.796, 0.786, 0.761, 0.794, 0.796, 0.789, 0.824, 0.807, 0.801, 0.806, 0.801, 0.787, 0.803, 0.796, 0.801, 0.791, 0.804, 0.800, 0.794, 0.797, 0.799, 0.799, 0.799, 0.792, 0.800, 0.798, 0.796, 0.796, 0.800, 0.798, 0.800, 0.799, 0.802, 0.799.

**Precision by raw score** (`runs/run-r18/val_dets_onnx.json`, from `tools/calibrate_scores.py`; validation, detections >= 0.01, labelled by greedy same-species IoU >= 0.5 matching):

| Raw score | Detections | Share that hit a real insect |
| :-- | --: | --: |
| 0.01-0.02 | 18,354 | 0.3% |
| 0.02-0.04 | 3,458 | 13.7% |
| 0.04-0.06 | 1,329 | 64.8% |
| 0.06-0.10 | 1,065 | 81.0% |
| 0.10-0.15 | 534 | 94.4% |
| 0.15-0.20 | 85 | 90.6% |
| 0.20-0.30 | 6 | 100.0% |

**Count error by density** (`runs/run-r18/base_vs_finetuned_val.json`, fine-tuned model, threshold 0.04, validation):

| Insects per photo (that species) | RBB photos | RBB MAE | WSB photos | WSB MAE |
| :-- | --: | --: | --: | --: |
| 1-9 | 148 | 0.77 | 42 | 2.33 |
| 10-29 | 38 | 2.66 | 47 | 6.32 |
| 30+ | 11 | 5.45 | 18 | 15.78 |

**ONNX export** (`models/rice-pest-r18-1.onnx`, 80,750,650 bytes = 80.75 MB; parity in `runs/run-r18/parity_val10.json`). Parity on 10 validation images at threshold 0.04: 126 detections compared, minimum box IoU 0.99999, maximum score difference 3.5e-07, 0 failures. Development note (2026-10-16, observed during development, not kept as an artefact): the first export traced the model in training mode and 0 of its 300 output rows matched PyTorch; exporting under `eval()` and `torch.no_grad()` fixed it, and `tests/test_export_onnx.py` guards the regression. Parity on the full test split, as the spec asks, has not been run. CPU latency on the reference laptop has not been measured.

## Run r50-1 plan (2026-10-16), not yet executed

Owner decisions (2026-10-16): the next run is the spec's fallback, RT-DETR-r50vd, at the same 640×640 contract, on a Colab **T4**.

- Base checkpoint: `PekingU/rtdetr_r50vd` pinned at revision `df939e661d8c52e80608d1ec566561aabd25a4e7` (resolved 2026-10-16 via HfApi.model_info; Apache-2.0).
- Notebook: `notebooks/train_colab_r50.ipynb`, generated by `python tools/build_notebook.py --revision df939e66… --variant r50` (has a `--check` mode). Run folder on Drive: `rice-pest-detector/run-r50`, so run r18-1's files are untouched.
- Changes from r18-1: batch 4 (r50 at batch 8 risks running out of a T4's 16 GB), 40 epochs (r18-1 peaked at epoch 3 of 60). Other settings are unchanged: learning rates, seed, fp16 with the float32 loss fix and the experiment fingerprint and resume checks. This is the first GPU run of the 2026-10-14 review fixes.
- Why r50 first: it keeps the whole pipeline, the ONNX contract, the app and the workshop's teaching CLI. A check on 2026-10-16 found that merging female and male scores into species scores barely moves r18-1 (highest score 0.251 → 0.266; validation count accuracy 0.632 → 0.648), so the low scores are not mainly the sex classes splitting the score. If r50 does not clearly cut the validation crowded-tray error (WSB 30+ MAE 15.8 for r18-1 at 0.04), the next lever is input resolution or a different detector family, both of which change the contract.

**Test-split exception (owner, 2026-10-16).** Run r18-1 used the spec's single test evaluation. The owner allows **one** further test look, for the chosen next model only, after its checkpoint, counting threshold and calibration have all been fixed on validation. The r50 notebook enforces this: its test cell refuses to run until `THRESHOLD` is set by hand to the validation-chosen value. After that look the test split has been seen twice; any public claim must say so.

Order after training: export r50 to ONNX with parity → validation analysis (`tools/compare_base_vs_finetuned.py`-style evaluation, `tools/calibrate_scores.py`, demo-threshold sweep) → decide on validation → set `THRESHOLD` → one test look → record here.

### Run r50-1: review corrections (2026-10-17)

A code and peer review of the r50 notebook (2026-10-17, static) was triaged:

- **Not a single-variable run.** Against r18-1, run r50-1 changes the backbone (r18 → r50), the batch (8 → 4 at the same learning rates, so twice the optimiser steps per epoch) and the schedule (60 → 40 epochs, with cosine annealing over 40). Any difference between r18 and r50 reflects all three. The plan above said "changes one thing"; that was wrong.
- **Training data repeats.** Train holds 1,179 photo families, many with several augmented copies, and there is no online augmentation, so each epoch passes over the same content several times. This fits both runs peaking early (r18-1 at epoch 3 of 60; r50-1 at epoch 4, counting from 0). The run was already in progress and the owner chose to let it finish; `best.pt` is selected on validation either way. For the next run: online augmentation, one copy per family per epoch, early-stopping patience, a learning-rate warmup and no weight decay on norms and biases.
- **Low raw scores are probably structural.** RT-DETR's class loss targets the matched box IoU, so small insects pull scores down whatever the backbone (inferred from the library design, not measured). r50-1 is judged on calibrated counts and crowded-tray error, never on raw counts at 0.5.
- **Test cell fixed before the test look** (r50 notebook only; r18 unchanged): the protocol check now runs before any cached test numbers are printed, and the result is written atomically.

### Run r50-1: pre-registered decision rules (owner, 2026-10-17)

Fixed before any calibrated or count-threshold r50-1 result was computed. While training, the per-epoch logs show only mAP and counts at 0.5, where neither model keeps any detection.

Both models are measured the same way on the 253 validation images. Each uses its own count-optimal threshold, the lowest total MAE on the `tools/choose_demo_threshold.py` grid, chosen inside 5 family-grouped folds (`tools/calibrate_scores.py`). Results are out-of-fold. r18-1's reference values are already recorded: count accuracy 0.632, WSB 30+ MAE 15.8.

1. **Test look (the owner's one exception).** Spend it on r50-1 only if r50-1's out-of-fold validation count accuracy is **≥ 0.80**, the count gate. Otherwise keep the look for the next recipe, and report r50-1 on validation only.
2. **Replacing r18-1 as the demo and workshop model.** Replace only if both hold:
   - (a) on the 18 validation images with 30 or more white stemborers (one image per family), a paired bootstrap shows r50-1's absolute WSB count error is lower: 10,000 resamples of images, seed 20261017, and the 95% interval of mean(r50 error − r18 error) lies entirely below 0;
   - (b) r50-1's out-of-fold count accuracy is not below r18-1's 0.632.

   A replacement re-runs the app fixtures and the emulator steps.

## Run r50-1 (2026-10-17), hosted-executed, validation only

Executed with the Colab CLI on a Colab **T4**. Session started 2026-10-16 17:53 UTC; the notebook ran for 27,055 s (7.5 h): about 20 min of data download and verification, then 40 epochs at about 11 min each. The notebook was the committed `notebooks/train_colab_r50.ipynb` (SHA-256 `b70038cb…`), run unchanged. Its last cell stopped at the locked test look, as designed. Executed copy and CLI log: `runs/run-r50/` (not tracked).

- **Checkpoint:** best validation species mAP50 **0.906 at epoch 4** (counting from 0). `best.pt` SHA-256 `80145a85f9731201b6effdc14e8079a5b512ba5ec2c1c1f2bcaecbde0c7599b7`.
- **Training curve:** epoch 0 0.857, epoch 2 0.883, epoch 4 0.906; then a decline to 0.68–0.75 from epoch 15 and a plateau at 0.72–0.74 through epoch 39, while training loss fell from 19.1 to 4.75. As with r18-1, this is an early peak followed by overfitting (see the review corrections above).
- **Four-class mAP50 at the best epoch:** 0.798 (r18-1 best: 0.704). Per class at epoch 4 (`runs/run-r50/history.jsonl`): RBB_FEMALE 0.820, RBB_MALE 0.836, WSB_FEMALE 0.661, WSB_MALE 0.874, so 1 of 4 classes is below the 0.70 sex-class bar. WSB_FEMALE stays the weakest class. Its best epoch was a different one (0.737 at epoch 8).
- **ONNX:** `models/rice-pest-r50-1.onnx`, 171,753,457 bytes, SHA-256 `fc0b2cf4a23f9c6ca2436f15433b78ff437881be38d6c32b189e5d6383cb886f`, opset 17, same contract. Parity on 10 validation images at 0.04: 112 detections compared, minimum box IoU 0.99998, maximum score difference 7.8e-7, 0 failures (`runs/run-r50/parity_val10.json`).

**Validation counts** (`tools/calibrate_scores.py`, 5 family-grouped folds, out-of-fold):

| Rule | r18-1 count accuracy | r50-1 count accuracy | r50-1 MAE RBB / WSB | r50-1 WSB 30+ MAE |
| :-- | --: | --: | --: | --: |
| Count-optimal threshold (0.04 in every fold, both models) | 0.632 | **0.751** | 0.80 / 1.94 | 11.9 |
| Calibrated p ≥ 0.5 (raw 0.043) | 0.597 | 0.727 | 1.00 / 1.86 | 11.4 |
| Expected count | 0.549 | 0.684 | 1.21 / 2.09 | 13.9 |

Calibration error falls from 0.288 to 0.028 out-of-fold with Platt scaling (a = 3.07, b = 9.50). Raw scores remain low, as the review expected: the highest validation score on any image is 0.3149 for r50-1 and 0.2514 for r18-1 (the maximum over the 253 images of each image's top score, from `runs/run-r50/val_dets_onnx.json` and `runs/run-r18/val_dets_onnx.json`). The wave-2 entry below traces the low scores to a training-library bug.

**Pre-registered rules, applied:**

1. **Test look: not spent.** r50-1's out-of-fold count accuracy is 0.751, below the 0.80 gate. The owner's one test exception stays unused for the next recipe.
2. **Replacing r18-1: both conditions met.** (a) On the 18 validation images with 30 or more white stemborers (18 families), the WSB absolute error falls from 15.78 (r18-1) to 11.89 (r50-1). The mean paired difference is −3.89, with a 95% bootstrap interval of [−7.56, −0.44] (10,000 resamples, seed 20261017), entirely below 0. r50-1 is better on 12 images and worse on 4. Signed bias: r18-1 +2.44, r50-1 +0.78. (b) Count accuracy 0.751 ≥ 0.632. Data: `runs/run-r50/dense_wsb_bootstrap.json`.

**r50-1 therefore replaces r18-1 as the demo and workshop model.** It is still exploratory and still below the count gate. The demo threshold stays 0.04, so the workshop's 0.04 wording does not change. The "count accuracy 0.632" caveat becomes 0.751. Raw 0.06 maps to about 74% calibrated probability for r50-1 (77% for r18-1), so the 0.06 review flag stands. Swap done on 2026-10-17: the workshop's sample photos and reference counts were re-run on validation photos, and the emulator steps and quoted numbers were updated. The app pins no model yet; its demo runs r50-1 placed with `demo.json` until a wave-2 model is chosen and released.

## Wave 2 (2026-10-17): the denoising-loss fix and two challengers. Pre-registered; all three results in

**Why.** Runs r18-1 and r50-1 were trained on transformers 4.57.6. In that version the main RT-DETR loss is computed over all decoder queries, including the 100 denoising queries: `modeling_rt_detr.py` sets `logits = outputs_class[:, -1]` and `loss_rt_detr.py` passes it to the criterion unsplit. Only the auxiliary outputs are split by `dn_num_split`; this was checked in the installed source on 2026-10-17. Both base configs set `num_denoising=100` and `auxiliary_loss=True`, so the bug was active. transformers v5.18.0 fixed it (PR #48528, "Fix D-FINE / RT-DETR main loss being computed over the denoising queries"). Inferred, not measured: Hungarian matching on the main loss can assign targets to noised ground-truth queries, which could explain the persistently low raw scores.

**Runs** (owner, 2026-10-17). All use the same family-grouped split, are judged on validation only and keep the r50-1 recipe unless stated otherwise:
1. **r50-v5**: RT-DETR-r50vd retrained on transformers ≥ 5.18 with the r50-1 recipe otherwise unchanged. This is the fair baseline.
2. **D-FINE-L**: `DFineForObjectDetection` from `ustc-community/dfine-large-coco` (COCO-only weights; the Objects365-pretrained variants may carry that dataset's terms), at 640 px with 300 queries.
3. **RF-DETR-M**: Apache-2.0 (N/S/M/L only), at its native 576 px. It starts after its preprocessing path is built and tested; runs 1 and 2 go first, in parallel.

**Pre-registered rules** (owner-approved 2026-10-17, before any wave-2 result). Every comparison uses out-of-fold validation counts at each model's validation-chosen threshold (`tools/calibrate_scores.py`, 5 family-grouped folds) and the paired bootstrap on the 18 validation images with 30 or more white stemborers (10,000 resamples, seed 20261017):

- **A. r50-v5 vs the current demo (r50-1).** r50-v5 replaces r50-1 only if the 95% interval of mean(r50-v5 error − r50-1 error) lies entirely below 0 and its count accuracy is not below r50-1's 0.751.
- **B. Challengers vs r50-v5.** D-FINE-L or RF-DETR-M replaces the demo model only if its count accuracy beats r50-v5's and the 95% interval of mean(challenger error − r50-v5 error) lies entirely below 0.
- **C. Test look.** It stays unspent unless a model reaches out-of-fold validation count accuracy ≥ 0.80; then only the best such model gets it, once.
- **D. Ship gates.** No model ships without ONNX ≤ 200 MB, parity on 10 validation images and a measured CPU latency ≤ 5 s per photo on the reference laptop.

### Wave 2 results as of 2026-10-17 (r50-v5 and RF-DETR-M), validation only

Both runs were executed with the Colab CLI on Colab **T4**s, 40 epochs each, with the committed notebooks run unchanged; their last cell stopped at the locked test look. r50-v5 ran 22,268 s (6.2 h) and RF-DETR-M 21,108 s (5.9 h), in parallel sessions. D-FINE-L was still training at the time; its first attempt was interrupted when the laptop driving the CLI restarted, and it resumed from the Drive checkpoint on 2026-10-17 at 10:40 UTC (its results follow below).

| | r50-1 (current demo) | **r50-v5** | RF-DETR-M |
| :-- | --: | --: | --: |
| Best epoch (from 0) / species mAP50 | 4 / 0.906 | 1 / **0.937** | 3 / 0.933 |
| Four-class mAP50 at the best epoch | 0.798 | **0.861** | 0.837 |
| RBB_F / RBB_M / WSB_F / WSB_M | 0.820 / 0.836 / 0.661 / 0.874 | 0.927 / 0.829 / 0.826 / 0.863 | 0.900 / 0.787 / 0.785 / 0.876 |
| Highest validation score on any image | 0.3149 | 0.9359 | 0.9485 |
| Calibration error, raw scores | 0.288 | 0.046 | 0.035 |
| Count-optimal threshold (per fold) | 0.04 (all) | 0.48 (4 folds), 0.50 (1) | 0.44–0.48 |
| **Count accuracy, out-of-fold** | 0.751 | **0.834** | **0.846** |
| MAE RBB / WSB | 0.80 / 1.94 | 0.23 / 1.40 | 0.28 / 1.38 |
| WSB 30+ MAE (18 images) | 11.89 | **8.67** | 9.56 |
| `best.pt` SHA-256 | `80145a85…` | `e0ae635d…` | `5122c68a…` |

- **The denoising-loss fix explains the low scores.** With the same recipe and backbone, r50-v5's top score rises from 0.31 to 0.94, its raw scores are close to calibrated (error 0.046), and its count-optimal threshold moves from 0.04 to 0.48. All four sex classes now clear the 0.70 bar on validation, for both new models.
- **Threshold grid edge.** The count-optimal search grid stops at 0.50 (`tools/choose_demo_threshold.py`). One r50-v5 fold chose 0.50, so its threshold may be capped by the grid. Recorded, not changed: the grid was fixed before these results.
- **Early peaks again.** Both runs reach their best validation species mAP50 within the first four epochs and then drift down slowly (r50-v5 0.908 and RF-DETR-M 0.891 at epoch 39), much less steeply than r50-1.

**Pre-registered rules, applied:**

- **A. r50-v5 vs r50-1: both conditions met.** On the 18 dense white-stemborer images, the WSB error falls from 11.89 to 8.67. The mean paired difference is −3.22, with a 95% bootstrap interval of [−7.17, −0.17] (10,000 resamples, seed 20261017), entirely below 0. r50-v5 is better on 12 images and worse on 5. Signed bias: r50-1 +0.78, r50-v5 −4.56 (r50-v5 undercounts dense trays). Count accuracy 0.834 ≥ 0.751. **r50-v5 qualifies to replace r50-1.** Data: `runs/run-r50v5/dense_wsb_bootstrap_vs_r50-1.json`. The bootstrap code reproduces the r50-1 vs r18-1 interval above exactly.
- **B. RF-DETR-M vs r50-v5: not met.** Count accuracy is higher (0.846 > 0.834), but the dense-tray interval is not below 0: WSB 30+ error 9.56 vs 8.67, mean paired difference +0.89, 95% interval [−0.72, +3.11]; better on 6 images, worse on 7. Data: `runs/run-rfdetr-m/dense_wsb_bootstrap_vs_r50-v5.json`.
- **C. Test look: not yet spent.** Both models clear 0.80 out-of-fold count accuracy, so the look becomes available, for one model, once, after D-FINE-L is judged.
- **D. Ship gates: both models pass.**

| Gate | r50-v5 | RF-DETR-M |
| :-- | --: | --: |
| ONNX size (≤ 200 MB) | 171.7 MB (`rice-pest-r50-v5.onnx`, SHA-256 `dc3927ae…`) | 122.0 MB (`rice-pest-rfdetr-m.onnx`, SHA-256 `07161f11…`), input 576×576 |
| Parity, 10 validation images at the operating threshold 0.48 | 145 detections, max score diff 4.9e-6, min IoU 0.99999, 0 failures | 127 detections, max score diff 5.1e-6, min IoU 0.99999, 0 failures |
| CPU latency per photo, median of 10 (≤ 5 s) | 1.14 s | 0.33 s |

Parity at 0.04, compared query by query: RF-DETR-M matched on all 717 queries. r50-v5 matched on 9 of 10 images; on one image a single query near the 0.04 cut held a different proposal in each runtime (score difference 0.059). The kept counts were equal on every image, and the check at the operating threshold is clean. The repo's sort-order parity check reports this as a failure at 0.04, because many near-equal low scores swap order; the query-aligned comparison is in `runs/run-r50v5/parity_query_val10.json`.

**Demo swap to r50-v5 (owner, 2026-10-17), before D-FINE-L is judged.** r50-v5 replaces r50-1 as the demo and workshop model now; if D-FINE-L wins under rule B, a second swap follows. The demo threshold changes from 0.04 to **0.48**, the count-optimal threshold chosen in four of five folds. The low-confidence review flag keeps its meaning (a counted detection under about 75% likely to be real) and moves from raw 0.06 to **0.64**: Platt scaling (a = 2.30, b = −0.26) maps 0.64 to 0.74, and observed precision is 71% at raw 0.60–0.64 and 80% at 0.64–0.70 (`runs/run-r50v5/val_dets_onnx.json`). At 0.48 / 0.64 the flag marks 100 of the 253 validation photos, against 101 for r50-1 at 0.04 / 0.06.

### D-FINE-L (2026-10-18), validation only

Executed with the Colab CLI on a Colab **T4**, 40 epochs, with the committed notebook `notebooks/train_colab_dfine-l.ipynb` run unchanged. Its first attempt was interrupted when the computer driving the CLI restarted; the run resumed from its Drive checkpoint at epoch 3 (counting from 0) and finished on 2026-10-17 at 17:47 UTC (25,617 s for the resumed part). Its last cell stopped at the locked test look, as designed.

| | r50-v5 (demo) | **D-FINE-L** |
| :-- | --: | --: |
| Best epoch (from 0) / species mAP50 | 1 / 0.937 | 3 / **0.940** |
| Four-class mAP50 at the best epoch | 0.861 | 0.848 |
| RBB_F / RBB_M / WSB_F / WSB_M | 0.927 / 0.829 / 0.826 / 0.863 | 0.933 / 0.777 / 0.819 / 0.864 |
| Highest validation score on any image | 0.9359 | 0.9590 |
| Calibration error, raw scores | 0.046 | 0.048 |
| Count-optimal threshold (per fold) | 0.48 (4 folds), 0.50 (1) | 0.50 (4 folds), 0.48 (1) |
| **Count accuracy, out-of-fold** | **0.834** | 0.822 |
| MAE RBB / WSB | 0.23 / 1.40 | 0.28 / 1.38 |
| WSB 30+ MAE (18 images) | 8.67 | 8.56 |
| `best.pt` SHA-256 | `e0ae635d…` | `758e2d12…` |

- **B. D-FINE-L vs r50-v5: not met.** Count accuracy is lower (0.822 < 0.834), which alone fails the rule. On the 18 dense white-stemborer images the error is a tie: 8.56 vs 8.67, mean paired difference −0.11, 95% interval [−0.89, +0.72] (10,000 resamples, seed 20261017); better on 8 images, worse on 5. Data: `runs/run-dfine-l/dense_wsb_bootstrap_vs_r50-v5.json`.
- **Threshold grid edge.** Four of five folds chose 0.50, the top of the pre-registered grid (`tools/choose_demo_threshold.py`), so D-FINE-L's count-optimal threshold may lie above it and its count accuracy may be understated. Recorded, not changed: the grid was fixed before any wave-2 result.
- **D. Ship gates: size and speed met; parity not met at the pre-registered tolerance.** ONNX `rice-pest-dfine-l.onnx` 125.2 MB (SHA-256 `c823f5d8…`); CPU 0.14 s per photo (median of 10). At threshold 0.48 on the 10 parity images (D-FINE-L counts at 0.50; parity was not run there), the kept detections and classes are identical and box IoU is 1.000, but scores differ by up to 2.95e-3, above the spec's 1e-3. At 0.04, query by query, the largest score difference is 7.5e-3 (minimum IoU 0.989) and two images differ by one or two detections near the cut. Data: `runs/run-dfine-l/parity_val10_t048.json`, `runs/run-dfine-l/parity_query_val10.json`.

**Result of wave 2.** r50-v5 stays the demo model: it met rule A, and neither challenger met rule B. Three models clear the 0.80 out-of-fold count-accuracy line (RF-DETR-M 0.846, r50-v5 0.834, D-FINE-L 0.822), so the single test look (rule C) is now available, for one model, once.

### Test look (rule C), 2026-10-18: r50-v5 at 0.48

**Owner decision (2026-10-18):** the single test look goes to r50-v5, the model the rules chose and the app ships, at its validation-chosen threshold 0.48. Run once, locally on CPU, with the repository's own evaluation code: the same `evaluation_id`, `check_cached_test`, `evaluate` and atomic write as the notebook's locked test cell; the model was rebuilt from the base config and `best.pt` loaded. The result is bound to the weights, manifest, annotations, threshold and evaluator version (`runs/run-r50v5/test_metrics.json`: `best.pt` `e0ae635d…`, manifest `d505f2d6…`, annotations `d602a8d8…`, threshold 0.48, evaluator version 2).

| Gate (`specs/001-model-training`, SC-002 to SC-006) | Test, 252 images | Validation, out-of-fold |
| :-- | --: | --: |
| Species mAP50 ≥ 0.80 | **0.943**: met | 0.937 |
| Count accuracy ≥ 0.80 | **0.849**: met (no-detection baseline 0.456) | 0.834 |
| Each sex class mAP50 ≥ 0.70 | **met**: RBB_F 0.894, RBB_M 0.798, WSB_F 0.874, WSB_M 0.876 (four-class 0.860) | all ≥ 0.826 |

- **Counts.** MAE RBB 0.47, WSB 1.01; signed bias +0.27 and +0.40 (a slight overcount on average); exact counts on 84% and 74% of images; presence recall 0.985 and 0.991.
- **Crowded trays.** WSB MAE by density: 1–9 insects 1.62, 10–29 1.68, 30+ 4.87 (23 images). RBB 30+: 3.65 (17 images). Crowded trays stay the weakest case, but less so than on validation (8.67 on 18 images); with this few images the difference may be the photos, not the model.
- **Confusion.** Most errors are within a species: RBB male read as female 86 times, WSB male as female 60 times. Cross-species errors are rare (8 in total). Missed insects: 180 of 3,320; spurious detections: 349.
- **Scores.** The median image's top score is 0.85 (p90 0.91, max 0.94): the scores carry over from validation.
- **Protocol note.** The test split has now had both looks the pre-registered rules allow: once by r18-1 (13 Oct) and once by r50-v5 (this look). The two challengers were also scored on it afterwards, by owner exception, post-hoc and for comparison only (next paragraph). No further test looks remain under the pre-registered rules; a later model needs a new held-out set, such as field photos.

**Post-hoc test evaluation of the two challengers (owner exception, 2026-10-18).** After r50-v5's look, the owner asked for RF-DETR-M and D-FINE-L to be evaluated on the same test split, each at its own validation-chosen threshold, with the same code (local CPU). This goes beyond rule C. It is reported for comparison only and was **not** used to choose a model: the demo model was fixed by rules A and B on validation before any test look. Files: `runs/run-rfdetr-m/test_metrics.json`, `runs/run-dfine-l/test_metrics.json` (each marked as a post-hoc exception).

| Test split, 252 images | r50-v5 (0.48) | RF-DETR-M (0.48, 576 px) | D-FINE-L (0.50) |
| :-- | --: | --: | --: |
| Species mAP50 | 0.943 | 0.944 | 0.946 |
| Four-class mAP50 | 0.860 | 0.853 | 0.845 |
| RBB_F / RBB_M / WSB_F / WSB_M | 0.894 / 0.798 / 0.874 / 0.876 | 0.891 / 0.783 / 0.852 / 0.887 | 0.868 / 0.748 / 0.883 / 0.882 |
| **Count accuracy** | **0.849** | 0.806 | 0.833 |
| MAE RBB / WSB | 0.47 / 1.01 | 0.58 / 1.08 | 0.55 / 1.07 |
| Signed bias RBB / WSB | +0.27 / +0.40 | +0.44 / −0.04 | +0.48 / +0.45 |
| WSB 30+ MAE (23 images) / RBB 30+ MAE (17) | 4.87 / 3.65 | 4.57 / 5.00 | 5.26 / 3.47 |
| Exact count, RBB / WSB | 84% / 74% | 84% / 68% | 84% / 71% |

All three meet the three model gates on test. The test results agree with the validation decision: mAP is level (0.943–0.946), and r50-v5 counts best. RF-DETR-M, the best counter on validation (0.846), is the weakest on test (0.806), a reminder that differences of a few points between these models are within run-to-run and split-to-split variation.

**Status after wave 2.** r50-v5 meets all three model quality gates on the held-out test split. The weights are published on Kaggle as a teaching demo (owner, 2026-10-18), so that gate is met. The release gates that remain (field validation on phone photos, a wording review of the English text and its Filipino draft, a data-protection review and a phone latency target) are still open, so the model stays a demo model. Every model carries a "Not validated" tag in the app (owner decision): none has been validated in the field or by experts.

### Parity check pairs detections (2026-10-18)

**What happened.** The first CI run on the public repository (Linux, transformers 5.20.1) failed two ONNX export tests that pass on Windows. Both compared ONNX Runtime and PyTorch outputs query by query, in order. The tests' tiny untrained RT-DETR gives every anchor the same encoder score under transformers 5.20.1 (its default initialisation, 0.01, lets each conv and eval-mode BatchNorm shrink the signal), so which 300 queries are selected, and in what order, came down to tie-breaking, which differs between the two runtimes on Linux. The export was not at fault. The local test runs had used a virtual environment still on transformers 4.57.6, so they did not exercise the pinned version.

**What changed (owner decision).** `tools/export_onnx.parity()` now pairs detections by class and highest box IoU instead of by list position; the tolerances (same kept detections, IoU ≥ 0.99, score difference ≤ 1e-3) are unchanged. The export regression test matches output rows one to one in the same way, and its tiny model uses `initializer_range=0.2`, so its outputs depend on the input (only 138–145 of 300 selected queries are shared between a blank image and a random one; the 300th/301st score gap on the test inputs is 1.2e-4 or more). A check confirmed the matcher accepts the same outputs in shuffled order and rejects outputs from a different input. Full suite on transformers 5.20.1: 128 passed.

**Effect on recorded results.** The parity figures above were computed with the order-based check and are not re-run. Pairing can only remove order-swap failures; the single r50-v5 query near the 0.04 cut that held a different proposal is a real difference and would still be reported.

### D-FINE-L parity at 0.50 and owner waiver (2026-10-18)

**Re-run.** Parity for D-FINE-L had been run only at 0.48, while the model counts at 0.50. It was re-run on the same 10 validation photos at 0.50 (and again at 0.48), with the ONNX file `rice-pest-dfine-l.onnx` (SHA-256 `c823f5d8…`) against the PyTorch checkpoint, using `parity()` after it was corrected to judge each photo on its own pairs (it had been comparing every photo after the first miss against the running maximum, so the earlier report listed images 5–9 where only 5 and 6 miss).

| Threshold | Detections compared | Kept detections and classes | Min box IoU | Max score difference | Photos over 1e-3 |
| :-- | --: | :-- | --: | --: | :-- |
| 0.50 | 149 | identical on all 10 | 0.99999 | 2.95e-3 | 2 of 10 (images 5 and 6) |
| 0.48 | 153 | identical on all 10 | 0.99999 | 2.95e-3 | 2 of 10 (images 5 and 6) |

Data: `runs/run-dfine-l/parity_val10_t050_rerun.json`, `runs/run-dfine-l/parity_val10_t048_rerun.json`.

**Owner decision (2026-10-18): waiver.** Because the kept detections, classes and boxes match at the counting threshold, and only scores differ (by at most 2.95e-3, which does not change any count), the owner waived the 1e-3 score tolerance for D-FINE-L as a teaching-demo comparison model. It stays on Kaggle and in the app's download list, with its "Not validated" tag. The tolerance itself is unchanged for any future model.
