---
description: "Task list for the rice-pest model training pipeline"
---

# Tasks: Rice-Pest Model Training

**Input**: Design documents from `/specs/001-model-training/`

**Prerequisites**: [plan.md](plan.md), [spec.md](spec.md), [research.md](research.md), [data-model.md](data-model.md), [contracts/](contracts/), [quickstart.md](quickstart.md)

**Status**: Implemented (Spec Kit record written 2026-10-19; the pipeline was first designed with a brainstorming workflow before Spec Kit was added to this repository). Done tasks are marked `[x]` with the evidence after `→`; open tasks are `[ ]`.

**Tests**: Required. Constitution Principle III (test-first) is non-negotiable: within each story the test tasks come first and must fail for the right reason before their implementation task. Tasks that record a run, a decision or a result have the evaluation record as their evidence instead.

**Organization**: Tasks are grouped by user story so each story can be built, tested and shown on its own.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependency on an unfinished task)
- **[Story]**: The user story the task belongs to (US1–US5)
- Paths are from the repository root

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: A Python 3.12 package that installs, tests and keeps large or secret files out of git.

- [x] T001 Create the package with `requires-python = ">=3.12,<3.13"`, numpy 2.5.4 and Pillow 12.3.0 pinned, the `train`, `export` and `dev` extras, and the `torch` and `onnx` pytest markers in `pyproject.toml` → `pyproject.toml`
- [x] T002 [P] Mirror the extras in `requirements.txt` and test that the two agree in `tests/test_requirements.py` → `requirements.txt`, `tests/test_requirements.py`
- [x] T003 [P] Exclude images, run folders, weights and checkpoints from git (`runs/`, `data/images/`, `*.onnx`, `*.pt`, `*.safetensors`, `models/*` except `models/*.manifest.json`) and force LF on `data/*.json` and the fixtures → `.gitignore`, `.gitattributes`
- [x] T004 [P] Add the CI workflow: Ubuntu, Python 3.12, CPU PyTorch, the whole pytest suite → `.github/workflows/tests.yml`
- [x] T005 Define the four class names and the class-to-species map in `src/rice_pest_detector/__init__.py` → `src/rice_pest_detector/__init__.py`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: The label parser, the inference contract and the metrics that every story uses.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

- [x] T006 [P] Write failing tests for label parsing: YOLO rows, polygon rows to boxes, mixed rows, 6- and 8-field rows rejected, non-finite coordinates, out-of-image boxes, a missing label file as an error → `tests/test_labels.py`
- [x] T007 [P] Write failing tests for the inference contract: shape, range, no normalisation, greyscale and RGBA, the inclusive threshold, box scaling, the `size` parameter → `tests/test_infer.py`
- [x] T008 [P] Write failing tests for the metrics: the ±10% / ±1 tolerance, species grouping, every species must pass, confusion, grouped mAP, count errors → `tests/test_metrics.py`
- [x] T009 [P] Implement `parse_labels`, `validate_boxes` and `load_label_file` in `src/rice_pest_detector/labels.py` → `src/rice_pest_detector/labels.py`
- [x] T010 [P] Implement `preprocess` and `postprocess` in `src/rice_pest_detector/infer.py` and write the contract in `docs/inference-contract.md` → `src/rice_pest_detector/infer.py`, `docs/inference-contract.md`, [contracts/inference-contract.md](contracts/inference-contract.md)
- [x] T011 [P] Implement `count_within_tolerance`, `species_counts`, `count_accuracy`, `count_errors`, `confusion` and `map50` (pycocotools, `maxDets = [1, 10, 300]`) in `src/rice_pest_detector/metrics.py` → `src/rice_pest_detector/metrics.py`

**Checkpoint**: Foundation ready; user stories can begin.

---

## Phase 3: User Story 1 - Split the open dataset without leakage (Priority: P1) 🎯 MVP

**Goal**: A committed, family-grouped, near-duplicate-free 70/15/15 split with no images in git.

**Independent Test**: Rebuild `data/` from the dataset and see no diff; `tests/test_committed_split.py` passes.

### Tests for User Story 1 ⚠️ write first, see them fail

- [x] T012 [P] [US1] Tests for family keys from Roboflow file names, and rejection of other names → `tests/test_families.py`
- [x] T013 [P] [US1] Tests for dHash stability and transitive group merging with singletons kept → `tests/test_dedup.py`
- [x] T014 [P] [US1] Tests for the species-mix stratum, a deterministic proportional group split and the evaluation-variant rule → `tests/test_split.py`
- [x] T015 [US1] Tests for the whole build on a synthetic dataset: no leakage, one colour variant per evaluation family, exclusions with reasons, the 300-box limit, COCO categories from 1, hashing of representatives only → `tests/test_manifest.py`
- [x] T016 [P] [US1] Test for the nearest cross-split neighbour report → `tests/test_nn_leakage_check.py`

### Implementation for User Story 1

- [x] T017 [P] [US1] Implement `family_key` in `src/rice_pest_detector/families.py` → `src/rice_pest_detector/families.py`
- [x] T018 [P] [US1] Implement `dhash` and `group_families` in `src/rice_pest_detector/dedup.py` → `src/rice_pest_detector/dedup.py`
- [x] T019 [P] [US1] Implement `stratum`, `split_groups` (seed 20261013) and `select_eval_variant` in `src/rice_pest_detector/split.py` → `src/rice_pest_detector/split.py`
- [x] T020 [US1] Implement `prepare` and the command line in `src/rice_pest_detector/manifest.py` (writes the split manifest, the three annotation files and the exclusions) → `src/rice_pest_detector/manifest.py`, [contracts/split-manifest.md](contracts/split-manifest.md)
- [x] T021 [US1] Measure group sizes at dHash distances 0–4 on the real dataset, choose `DEDUP_MAX_DISTANCE = 1` by the 2% rule, and reject all-variant hashing → `src/rice_pest_detector/manifest.py`, `docs/evaluation-record.md` ("Near-duplicate threshold")
- [x] T022 [US1] Build `data/` from the dataset and record the result and checks (sizes, 0 leakage, 1 exclusion, selection rules, polygon boxes, build environment) → `data/split_manifest.json`, `data/annotations_train.json`, `data/annotations_val.json`, `data/annotations_test.json`, `data/exclusions.json`, `docs/evaluation-record.md` ("Result")
- [x] T023 [US1] Add tests that read the committed split: no family, group or file hash in two splits, sizes and seed, one image per family in val and test, annotation files equal to the manifest → `tests/test_committed_split.py`
- [x] T024 [P] [US1] Implement `tools/nn_leakage_check.py` and record the distances for validation and test → `tools/nn_leakage_check.py`, `docs/evaluation-record.md` ("Cross-split nearest-neighbour check")
- [x] T025 [P] [US1] Credit the dataset and list every change made to it → `data/README.md`, `NOTICE`, README ("Dataset")
- [ ] T026 [US1] Inspect by eye the three test pairs with pixel correlation above 0.95 (`img_2657` / `img_1918`, `img_2427` / `img_2267`, `img_2569` / `img_2308`) and record the outcome in `docs/evaluation-record.md`

**Checkpoint**: The split exists, is tested and can be rebuilt: the MVP every later number depends on.

---

## Phase 4: User Story 2 - Train a detector reproducibly on a free cloud GPU (Priority: P2)

**Goal**: Generated notebooks that download and verify the data, train resumably and choose the checkpoint on validation.

**Independent Test**: `tests/test_build_notebook.py` and `tests/test_train.py` pass; each committed notebook equals a fresh build.

### Tests for User Story 2 ⚠️ write first, see them fail

- [x] T027 [P] [US2] Tests for the download (verify size, MD5 and SHA-256; remove the partial file on a mismatch or a mid-stream error) and the extraction (names a missing member, checks each digest, refuses path traversal) → `tests/test_fetch.py`
- [x] T028 [P] [US2] Tests for the training loop: collate, checkpoint round trip, float32 loss under autocast, best checkpoint carrying its own score, legacy best checkpoint, refusing a different experiment, restoring random state, truncated history, skipped updates, divergence stop, resume not overwriting a better best, NaN scores, input size in the fingerprint → `tests/test_train.py`
- [x] T029 [P] [US2] Tests for the notebook generator: modules and revision embedded, no outputs or tokens, deterministic, data round trip, GPU stop, fetch and env-log cells, Drive space warning, each variant's model, run folder, batch, `transformers` pin and input size, r18 unchanged, dataset credit for new variants → `tests/test_build_notebook.py`

### Implementation for User Story 2

- [x] T030 [P] [US2] Implement `download` and `extract_members` with the archive pins, and record where the pins come from → `src/rice_pest_detector/fetch.py`, `docs/evaluation-record.md` ("Colab data path")
- [x] T031 [US2] Implement `TrainConfig`, `ManifestDataset`, `build_model`, `fp32_loss`, the experiment fingerprint, atomic checkpoints, history handling and `fit` (best checkpoint on validation species mAP50 only) → `src/rice_pest_detector/train.py`
- [x] T032 [US2] Implement `tools/build_notebook.py` (24 cells, embedded modules and data, fixed ids, `--check`) → `tools/build_notebook.py`, [contracts/notebook-generator.md](contracts/notebook-generator.md)
- [x] T033 [US2] Generate the r18 notebook, run r18-1 on Colab and record it (epoch 3 of 60; test look at 0.5: species mAP50 0.835, count accuracy 0.456 equal to the baseline, 0 detections kept) → `notebooks/train_colab.ipynb`, `docs/evaluation-record.md` ("Run r18-1")
- [x] T034 [US2] Apply the 2026-10-14 review fixes (float32 matcher and losses, skipped updates logged, atomic best checkpoint, resume identity, truncated history, bound test result, GPU stop, EXIF scan, LF line endings) → `src/rice_pest_detector/train.py`, `tools/build_notebook.py`, `docs/evaluation-record.md` ("Review fixes")
- [x] T035 [US2] Add the r50 variant (batch 4, 40 epochs, own run folder, Drive mount skipped when already mounted), run r50-1 on a T4 and record it (validation only: species mAP50 0.906 at epoch 4) → `notebooks/train_colab_r50.ipynb`, `docs/evaluation-record.md` ("Run r50-1")
- [x] T036 [US2] Trace the low raw scores to the `transformers` 4.57.6 denoising-loss bug and pin `transformers` 5.20.1 for new runs → `pyproject.toml`, `requirements.txt`, `docs/evaluation-record.md` ("Wave 2"), [research.md](research.md) R9
- [x] T037 [US2] Add the wave-2 variants (r50v5; dfine-l; rfdetr-m at 576 px with `input_size` through training and the test cell) and record their runs on T4s, 40 epochs each → `notebooks/train_colab_r50v5.ipynb`, `notebooks/train_colab_dfine-l.ipynb`, `notebooks/train_colab_rfdetr-m.ipynb`, `docs/evaluation-record.md` ("Wave 2 results", "D-FINE-L")
- [x] T038 [US2] Confirm that all five committed notebooks equal a fresh build (2026-10-19) → [contracts/notebook-generator.md](contracts/notebook-generator.md)
- [ ] T039 [US2] Build the next training recipe recorded in the evaluation record (online augmentation, one copy per family per epoch, early-stopping patience, a learning-rate warmup, no weight decay on norms and biases) in `src/rice_pest_detector/train.py`, test first in `tests/test_train.py`

**Checkpoint**: Any variant can be regenerated, checked and rerun from a browser.

---

## Phase 5: User Story 3 - Judge a model by rules fixed before the results (Priority: P3)

**Goal**: A threshold, a calibration and a model choice made on validation by written rules, and one recorded test look.

**Independent Test**: The threshold and calibration tools reproduce their results on saved validation detections; a cached test result is refused after any change to what it depends on.

### Tests for User Story 3 ⚠️ write first, see them fail

- [x] T040 [P] [US3] Tests for `evaluate` (count errors, baseline and score quantiles; mismatched COCO file refused) and for the bound test result → `tests/test_train.py`
- [x] T041 [P] [US3] Tests for the threshold sweep (count errors per threshold; lowest error, higher threshold on ties; the grid spans low scores and includes 0.5) → `tests/test_choose_demo_threshold.py`
- [x] T042 [P] [US3] Tests for calibration (greedy same-species labelling in score order, Platt fit, threshold inversion, calibration error, family folds, convergence on cached detections, the model's input size) → `tests/test_calibrate_scores.py`

### Implementation for User Story 3

- [x] T043 [US3] Implement `evaluate`, `evaluation_id`, `check_cached_test` and `EVALUATOR_VERSION = 2`, and the locked test cell (`THRESHOLD = None`, protocol check before cached numbers, atomic write) → `src/rice_pest_detector/train.py`, `tools/build_notebook.py`, [contracts/evaluation-reporting.md](contracts/evaluation-reporting.md)
- [x] T044 [P] [US3] Implement `tools/compare_base_vs_finetuned.py` and record base against fine-tuned on validation → `tools/compare_base_vs_finetuned.py`, `docs/evaluation-record.md` ("Base vs fine-tuned")
- [x] T045 [P] [US3] Implement `tools/choose_demo_threshold.py` (validation only, grid 0.02–0.50) → `tools/choose_demo_threshold.py`
- [x] T046 [US3] Implement `tools/calibrate_scores.py` (Platt scaling, 5 family-grouped folds, out-of-fold counts, detection cache) and record r18-1's calibration → `tools/calibrate_scores.py`, `docs/evaluation-record.md` ("Score calibration")
- [x] T047 [US3] Write the r50-1 decision rules before its calibrated results, then apply them (no test look; r50-1 replaces r18-1 by the dense-tray bootstrap) → `docs/evaluation-record.md` ("Run r50-1: pre-registered decision rules", "Run r50-1")
- [x] T048 [US3] Write rules A–D before any wave-2 result → `docs/evaluation-record.md` ("Wave 2", "Pre-registered rules")
- [x] T049 [US3] Run the dense-tray paired bootstraps (18 validation photos, 10,000 resamples, seed 20261017) and apply rules A and B: r50-v5 replaces r50-1; neither RF-DETR-M nor D-FINE-L replaces r50-v5 → `docs/evaluation-record.md` ("Pre-registered rules, applied", "D-FINE-L"), README ("How r50-v5 was chosen")
- [x] T050 [US3] Choose r50-v5's threshold (0.48) and review level (0.64) on validation → `models/rice-pest-r50-v5.manifest.json`, `docs/evaluation-record.md` ("Demo swap to r50-v5"), README ("Choosing a demo threshold")
- [x] T051 [US3] Spend the rule-C test look on r50-v5 at 0.48 and record it (species mAP50 0.943, count accuracy 0.849 against a baseline of 0.456, each sex class ≥ 0.798) → `docs/evaluation-record.md` ("Test look (rule C)"), README ("Status and release gates")
- [x] T052 [US3] Record the post-hoc test evaluation of the two challengers, by owner exception, as comparison only → `docs/evaluation-record.md` ("Post-hoc test evaluation of the two challengers")
- [ ] T053 [US3] Assemble a new held-out set before any later model is judged (the test split has had its looks), and write its rules into `docs/evaluation-record.md` before the first result

**Checkpoint**: A model is chosen and its test result recorded under rules written before the results.

---

## Phase 6: User Story 4 - Export a model that runs on a laptop CPU and a phone (Priority: P4)

**Goal**: ONNX files that match PyTorch, fit the size and CPU gates, and a contract with golden fixtures for the apps.

**Independent Test**: `tests/test_export_onnx.py` and `tests/test_export_app_fixtures.py` pass; `python -m tools.export_app_fixtures --check` exits 0.

### Tests for User Story 4 ⚠️ write first, see them fail

- [x] T054 [P] [US4] Tests for the export: the graph honours the contract, outputs match PyTorch on inputs not used for the export, the parity report uses the tolerances and judges each image on its own pairs, a different model is flagged, the input size is a parameter, RF-DETR's position embeddings are frozen and match eager mode → `tests/test_export_onnx.py`
- [x] T055 [P] [US4] Tests for the golden fixtures: the pattern image, the contract block, the orientations against `exif_transpose`, the resize against Pillow, the postprocess boundary, and `--check` detecting a stale file → `tests/test_export_app_fixtures.py`

### Implementation for User Story 4

- [x] T056 [US4] Implement `export_onnx` (opset 17, `eval()` and `no_grad()`, contract names, static shape, frozen position embeddings), `parity` (paired by class and IoU) and `load_trained` → `tools/export_onnx.py`
- [x] T057 [P] [US4] Implement the fixture writers with `--check` and generate the fixtures → `tools/export_app_fixtures.py`, `app/tool/export_resize_fixtures.py`, `app/test/fixtures/contract_fixtures.json`, `app/test/fixtures/resize_fixtures.json`
- [x] T058 [US4] Run both fixture checks in CI → `.github/workflows/tests.yml`
- [x] T059 [US4] Export r50-v5, RF-DETR-M and D-FINE-L and check size (171.7, 122.0 and 125.2 MB) and parity on 10 validation photos at the operating threshold → `docs/evaluation-record.md` ("D. Ship gates")
- [x] T060 [US4] Measure CPU time per photo on the reference laptop, median of 10 (1.14 s, 0.33 s, 0.14 s) → `docs/evaluation-record.md` ("D. Ship gates", "D-FINE-L"), README ("Models")
- [x] T061 [US4] Change parity from order-based to paired after the first public CI run failed on Linux, keeping the tolerances → `tools/export_onnx.py`, `tests/test_export_onnx.py`, `docs/evaluation-record.md` ("Parity check pairs detections")
- [x] T062 [US4] Re-run D-FINE-L parity at 0.50 and record the score-tolerance waiver → `docs/evaluation-record.md` ("D-FINE-L parity at 0.50 and owner waiver"), `docs/decisions.md`, `models/rice-pest-dfine-l.manifest.json` (`notes`)
- [ ] T063 [US4] Set a per-photo latency target on a reference low-end phone (proposed ≤ 5 s) and measure the default model against it (release gate 6), with the phone app of [002-mobile-app](../002-mobile-app/spec.md); record it in `docs/evaluation-record.md`

**Checkpoint**: Three exported models meet the size and CPU gates and the apps can prove they follow the contract.

---

## Phase 7: User Story 5 - Publish the weights for teaching, and only for teaching (Priority: P5)

**Goal**: Three published models with strict manifests, cards and pinned downloads, and nothing heavy in git.

**Independent Test**: A downloaded model's size and SHA-256 equal its manifest; the app's catalogue test passes.

### Tests for User Story 5 ⚠️ write first, see them fail

- [x] T064 [US5] Test that the app's catalogue lists the three published models with https URLs, r50-v5 first as the default, and that each catalogue manifest equals the file in `models/` → `app/test/published_models_test.dart`

### Implementation for User Story 5

- [x] T065 [P] [US5] Write the three manifests with `"validated": false` → `models/rice-pest-r50-v5.manifest.json`, `models/rice-pest-rfdetr-m.manifest.json`, `models/rice-pest-dfine-l.manifest.json`, [contracts/model-manifest.md](contracts/model-manifest.md)
- [x] T066 [P] [US5] Write a model card per model and an index with the teaching-demo notice → `docs/model-card.md`, `docs/model-cards/r50-v5.md`, `docs/model-cards/rf-detr-m.md`, `docs/model-cards/d-fine-l.md`
- [x] T067 [US5] Publish the three ONNX files on Kaggle as one model with three variations (Apache-2.0, dataset credited), keep version 3 only → README ("Models"), `docs/decisions.md` (18 Oct)
- [x] T068 [US5] Point the app's catalogue and pin at the published files → `app/assets/model_catalog.json`, `app/assets/model_pin.json`, README ("Release gates", gate 3)
- [x] T069 [P] [US5] Record licences and how to cite → `NOTICE`, `CITATION.cff`, `LICENSE`
- [ ] T070 [US5] Build a field validation set (release gate 2): consented phone photos taken in the field, labelled by experts and scored with `count_errors`, after a data-protection review of the consent (release gate 5); record it in `docs/evaluation-record.md`

**Checkpoint**: The published models can be downloaded, checked and used by the apps, and say what they are for.

---

## Phase 8: Polish & Cross-Cutting Concerns

- [x] T071 [P] Document the pipeline in the README (Dataset, Architecture, Status and release gates, Quick start, Data pipeline, Training on Colab, Evaluation, Export to ONNX and parity, Choosing a demo threshold, Inference contract, Testing, Out of scope) → `README.md`
- [x] T072 [P] Record the figures quoted in the teaching decks with their sources → `docs/evaluation-record.md` ("Figures used in the teaching decks")
- [ ] T073 [P] Run `tools/build_notebook.py --check` for all five variants in CI → `.github/workflows/tests.yml` (see the plan's Complexity Tracking)
- [ ] T074 Run [quickstart.md](quickstart.md) from a fresh clone on one OS and fix anything it misses

---

## Dependencies & Execution Order

### Phase dependencies

- **Setup (Phase 1)** → **Foundational (Phase 2)** → user stories.
- **User stories (Phases 3–7)** run in priority order, because each consumes the previous one's output: US1 (the split) → US2 (training on it) → US3 (judging the runs) → US4 (exporting the chosen checkpoint) → US5 (publishing it). Each can still be tested on its own: US2 with the committed split, US3 with saved validation detections, US4 with a tiny untrained model, US5 with the committed manifests.
- **Polish (Phase 8)** after the stories it documents or checks.

### Within each story

- Tests first, failing for the right reason (Principle III).
- Package modules before the tools and notebooks that embed or call them.
- Rules are written into the evaluation record before the results they govern (T047 before r50-1's calibrated results; T048 before any wave-2 result; T048 before T051).
- Each story ends with the whole `pytest` suite green.

### Parallel opportunities

- T002, T003 and T004 together; T006, T007 and T008 together, then T009, T010 and T011.
- US1: T012, T013, T014 and T016 together; then T017, T018 and T019.
- US2: T027, T028 and T029 together; the r50-v5 and RF-DETR-M runs in T037 ran in parallel Colab sessions.
- US3: T040, T041 and T042 together; T044 and T045 together.
- US4: T054 and T055 together; T056 and T057 together.
- US5: T065, T066 and T069 together.

## Parallel example: User Story 1

```text
Task: "T012 Tests for family keys in tests/test_families.py"
Task: "T013 Tests for dHash and grouping in tests/test_dedup.py"
Task: "T014 Tests for the stratified split in tests/test_split.py"
Task: "T016 Test for the nearest-neighbour report in tests/test_nn_leakage_check.py"
```

## Implementation Strategy

### MVP first (User Story 1 only)

1. Phase 1 and Phase 2.
2. Phase 3 (US1): **stop and validate** that the split has no leakage (T023) before any training, because every later number depends on it.

### Incremental delivery (as it happened)

US1 (split, 13 Oct) → US2 and US3 alternating over five runs (r18-1 on 13 Oct; review fixes 14 Oct; calibration 16 Oct; r50-1 and the rules 16–17 Oct; wave 2 and the test look 17–18 Oct) → US4 (export and parity for each candidate) → US5 (publishing, 18 Oct).

### Open work

| Task | What | Blocks |
| :-- | :-- | :-- |
| T026 | Inspect three close test pairs by eye | Nothing; a check on the split |
| T039 | The next training recipe | A future run |
| T053 | A new held-out set | Judging any later model on held-out data |
| T063 | Phone latency target and measurement | Release gate 6 |
| T070 | Field validation set with a data-protection review | Release gates 2 and 5; any use beyond the teaching demo |
| T073 | Notebook `--check` in CI | Full compliance with Principle III |
| T074 | Quickstart from a fresh clone | Nothing |

Release gate 4 (the wording review of the app's English text and its Filipino draft by a native speaker) concerns app text and is tracked with [002-mobile-app](../002-mobile-app/spec.md).
