# Implementation Plan: Rice-Pest Model Training

**Branch**: `001-model-training` | **Date**: 2026-10-19 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/001-model-training/spec.md`

**Status**: Implemented (Spec Kit record written 2026-10-19; the pipeline was first designed with a brainstorming workflow before Spec Kit was added to this repository)

## Summary

A Python package (`src/rice_pest_detector/`) turns the open light-trap dataset by its authors (Deleña et al.) into a family-grouped, near-duplicate-free 70/15/15 split stored as JSON in `data/`; a generator (`tools/build_notebook.py`) embeds that package and data into Colab notebooks that fine-tune COCO-pretrained detection transformers (RT-DETR, RF-DETR, D-FINE) from Hugging Face `transformers` on a T4; command-line tools in `tools/` choose the counting threshold and calibrate scores on validation only, export the chosen checkpoint to ONNX and check parity with PyTorch; the inference contract (`docs/inference-contract.md`, reference `src/rice_pest_detector/infer.py`) and its golden fixtures hand the model to the apps. The decisions behind each step are in [research.md](research.md); the key ones are the family-grouped re-split (R1), counting accuracy beside a do-nothing baseline as the headline (R4, R5), the move to `transformers` 5.20.1 after the denoising-loss bug (R9) and the choice of r50-v5 by pre-registered rules (R7, R10).

## Technical Context

**Language/Version**: Python 3.12 (`requires-python = ">=3.12,<3.13"` in `pyproject.toml`)

**Primary Dependencies**: numpy 2.5.4 and Pillow 12.3.0 (pinned: `data/` and the app's resize fixtures were built with them); `train` extra: PyTorch, `transformers` 5.20.1 (4.57.6 for the two earlier runs, still pinned in their notebooks), pycocotools ≥ 2.0.8, scipy ≥ 1.11; `export` extra: onnx ≥ 1.16, onnxruntime ≥ 1.18 (tested 1.31.0); `dev` extra: pytest ≥ 8, ruff ≥ 0.5, nbformat ≥ 5.10

**Storage**: Files only. Committed: `data/split_manifest.json`, `data/annotations_{train,val,test}.json`, `data/exclusions.json` (19.4 MB in all), `notebooks/*.ipynb`, `models/*.manifest.json`, `app/test/fixtures/contract_fixtures.json`. Not committed: images, `runs/<run folder>/` (checkpoints, histories, test results, caches), `models/*.onnx`. Training writes to a run folder on Google Drive.

**Testing**: pytest, 142 tests, with `torch` and `onnx` markers that skip when those libraries are absent; CI (`.github/workflows/tests.yml`, Ubuntu, Python 3.12, CPU PyTorch) runs the whole suite plus `tools.export_app_fixtures --check` and `app/tool/export_resize_fixtures.py --check`

**Target Platform**: Training on Google Colab with a T4 GPU (16 GB), run from a browser or the Colab CLI; data preparation, evaluation, calibration and export on a Windows, macOS or Linux laptop CPU; the exported model runs under ONNX Runtime on a laptop CPU and in the Android app (ONNX Runtime 1.28.0 through `flutter_onnxruntime` 1.9.0, feature [002-mobile-app](../002-mobile-app/spec.md))

**Project Type**: Single project: a Python library, command-line tools and generated notebooks

**Performance Goals**: ONNX ≤ 200 MB and CPU time ≤ 5 s per photo (median of 10) on the reference laptop (rule D); training fits a T4 at batch 4 (about 11 min per epoch for r50 at 640 px, from the r50-1 run)

**Constraints**: The test split is used only under pre-registered rules (Principle IV); no image, checkpoint or weight file is committed; 300 detection queries (trays hold up to 106 insects); the input is a square 640 px (576 px for RF-DETR-M) with no normalisation

**Scale/Scope**: 5,453 images (4,948 / 253 / 252), 1,684 families, 1,600 duplicate groups, 71,047 boxes, 4 classes; 10 package modules, 7 Python tools, 5 notebooks; 5 training runs, 3 published models

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Checked against `.specify/memory/constitution.md` v1.0.0. The constitution was ratified on 2026-10-19, after the pipeline was built, so "before research" records how the design stood before the decisions in research.md and "after design" records the built pipeline.

| Principle | Check | Before research | After design |
| :-- | :-- | :-- | :-- |
| I. Teaching demo | Model cards and the README notice describe every model as a teaching demo, not validated, not for farmers, with no treatment advice | Pass | Pass: `docs/model-card.md` and `docs/model-cards/*.md` carry the notice; every manifest has `"validated": false` |
| II. One inference contract | `docs/inference-contract.md` and `src/rice_pest_detector/infer.py` define it; training, evaluation, threshold choice, calibration and export all call `preprocess`/`postprocess`; `tools/export_app_fixtures.py` writes the golden fixtures | Pass | Pass: per-model `input_size` (576 for RF-DETR-M) is a parameter of the same contract, not a second contract ([contracts/inference-contract.md](contracts/inference-contract.md)) |
| III. Test-first, green before done | Every module and tool has a pytest file; generated notebooks and fixtures have `--check` | Pass | **Gap**: CI runs the fixture checks but not `tools/build_notebook.py --check` (see Complexity Tracking; all five notebooks matched a fresh build on 2026-10-19) |
| IV. Rules fixed before results | Checkpoint chosen on validation; threshold and calibration on validation; rules A–D written before wave-2 results; test results bound to their full identity | Pass | Pass, with two recorded exceptions (see Complexity Tracking): the post-hoc test evaluation of the two challengers and the D-FINE-L parity waiver |
| V. Photos stay on the device | No photos of users are collected; tools make no network calls except the dataset download in the notebook | Pass | Pass: not otherwise applicable to a training pipeline |
| VI. Verified models only | Each published model has a strict manifest with size and SHA-256; the export record carries the checkpoint's SHA-256 | Pass | Pass: `app/test/published_models_test.dart` keeps the app's catalogue equal to `models/*.manifest.json` |
| VII. Shared sources, simplest thing | One package used by the notebooks (embedded), the tools and the tests; one split in `data/`; manifests in one place | Pass | Pass: no new dependency beyond those listed above |
| Additional constraints | No weights, `.env` or credentials committed; dataset credited as "its authors (Deleña et al.)"; licences in `NOTICE` and model cards | Pass | Pass: `.gitignore` excludes `*.onnx`, `*.pt`, `*.safetensors`, `runs/`, `models/*` except manifests |

## Project Structure

### Documentation (this feature)

```text
specs/001-model-training/
├── plan.md              # This file
├── research.md          # Phase 0: decisions and their alternatives
├── data-model.md        # Phase 1: entities, files and states
├── quickstart.md        # Phase 1: rebuild, train, judge, export, check
├── contracts/
│   ├── split-manifest.md         # data/split_manifest.json and the annotation files
│   ├── inference-contract.md     # photo to counts, as infer.py implements it
│   ├── model-manifest.md         # models/*.manifest.json and the export record
│   ├── evaluation-reporting.md   # evaluation results, gates and how they are recorded
│   └── notebook-generator.md     # tools/build_notebook.py and its --check
├── checklists/
│   └── requirements.md  # Spec quality checklist
└── tasks.md             # Phase 2 (/speckit-tasks)
```

### Source Code (repository root)

```text
src/rice_pest_detector/
├── __init__.py          # CLASS_NAMES, SPECIES_OF_CLASS
├── families.py          # Roboflow file name -> family key
├── labels.py            # YOLO rows and polygons -> boxes; validation
├── dedup.py             # dHash and near-duplicate grouping
├── split.py             # stratified 70/15/15 group split; eval-variant rule
├── manifest.py          # builds data/ from the dataset (DEDUP_MAX_DISTANCE = 1)
├── fetch.py             # one-request download with size/MD5/SHA-256 pins; verified extraction
├── infer.py             # the inference contract (reference implementation)
├── metrics.py           # mAP50 (pycocotools), count accuracy, count errors, confusion
└── train.py             # fine-tuning loop, checkpoints, evaluate(), test-result identity

tools/
├── build_notebook.py         # notebook generator (+ --check)
├── nn_leakage_check.py       # nearest cross-split neighbours, for inspection
├── compare_base_vs_finetuned.py
├── choose_demo_threshold.py  # validation-only threshold sweep
├── calibrate_scores.py       # Platt calibration, out-of-fold counts
├── export_onnx.py            # checkpoint -> ONNX; parity()
└── export_app_fixtures.py    # golden fixtures for the app (+ --check)

data/                    # split_manifest.json, annotations_*.json, exclusions.json, README.md
notebooks/               # train_colab.ipynb (r18), _r50, _r50v5, _dfine-l, _rfdetr-m (generated)
models/                  # rice-pest-{r50-v5,rfdetr-m,dfine-l}.manifest.json
tests/                   # one test file per module and tool, plus test_committed_split.py
docs/                    # inference-contract.md, evaluation-record.md, decisions.md, model-card.md, model-cards/
.github/workflows/tests.yml
```

**Structure Decision**: One Python package with thin command-line tools around it. The notebooks are build products of the package and `data/`, not a second copy of the code. The apps ([002-mobile-app](../002-mobile-app/spec.md), [003-desktop-app](../003-desktop-app/spec.md)) consume only the contract, the golden fixtures and the model manifests.

## Complexity Tracking

| Deviation | Why it stands | Simpler alternative rejected because |
| :-- | :-- | :-- |
| CI does not run `tools/build_notebook.py --check` (Principle III asks CI to run every `--check`) | The generator's behaviour is covered by `tests/test_build_notebook.py`, and all five committed notebooks matched a fresh build on 2026-10-19; adding the five checks to CI is an open task (T073) | Not a design choice to keep: it is recorded here so that it is fixed, not forgotten |
| The two challengers were evaluated on the test split after r50-v5's pre-registered look (Principle IV) | As `docs/evaluation-record.md` states: by owner exception, post-hoc, for comparison only, and not used to choose a model; the result files are marked as post-hoc | Leaving the figures out would hide numbers that the README already publishes |
| D-FINE-L's parity score tolerance (1e-3) is waived (rule D) | Kept detections, classes and boxes are identical at 0.48 and 0.50; scores differ by at most 2.95e-3, which changes no count; recorded in `docs/decisions.md` and the evaluation record; the tolerance stays for any future model | D-FINE-L is a comparison model in the app, not the default |
