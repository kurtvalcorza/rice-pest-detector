# Research: Rice-Pest Model Training

**Feature**: [spec.md](spec.md) | **Plan**: [plan.md](plan.md) | **Date**: 2026-10-19

The decisions below were made while the pipeline was built (13–18 October 2026) and are recorded in `docs/evaluation-record.md`, `docs/decisions.md`, `data/README.md` and the README. This file collects them in Spec Kit's Decision / Rationale / Alternatives form. Every figure is taken from those files.

## R0. The source dataset as found (checked 2026-10-13)

These facts were checked on the downloaded archive before any design decision, and the decks quote them.

- **Source:** the light-trap rice pest dataset by its authors (Deleña et al.), Zenodo DOI 10.5281/zenodo.20066074, CC BY 4.0. The extracted archive holds 112,898 files.
- **Classes:** `0 RBB_FEMALE`, `1 RBB_MALE`, `2 WSB_FEMALE`, `3 WSB_MALE`: rice black bug (*Scotinophara coarctata*) and white stemborer (*Scirpophaga innotata*).
- **Published split:** train 6,760 images in 1,353 source-file families (about five augmented variants each); valid 169 images, 169 families; test 169 images, 168 families. One family crosses the published train and test splits.
- **No pest-free images** in any split (0 empty label files). Trays hold up to 106 insects, so the detector needs room for many boxes per photo (RT-DETR's 300 queries, not a 100-query cap).
- **Labels:** 652 label files contain polygon rows (101 of them mixed with box rows); polygons are converted to boxes (FR-005).
- **Caveats:** capture date, place and trap fields are blank in all 7,098 metadata rows; images were pre-stretched to 640×640 before release; the annotations are not documented as human-verified.

## R1. Split: family-grouped re-split instead of the published split

**Decision**: Re-split the dataset 70/15/15 by family group, stratified by species mix (rice black bug only, white stemborer only, both), with seed `20261013` (`src/rice_pest_detector/split.py`, `manifest.py`). A family is an original photo and its augmented variants, recognised by the file-name prefix before `_jpg.rf.` (`families.py`).

**Rationale**: The published training split holds several augmented variants of each photo, and the README records that the published split has one family crossing train and test. A score on a split that holds copies of training photos measures memory, not counting. Grouping by family puts every copy of one tray on one side. The result is 1,179 / 253 / 252 families (70.0 / 15.0 / 15.0%) and 4,948 / 253 / 252 images.

**Alternatives considered**:

| Option | For | Against |
| :-- | :-- | :-- |
| The published train/valid/test split | Comparable with the authors' own benchmark | Copies of one tray on both sides; a family crosses train and test |
| Random image-level split | Simple | Augmented variants of one tray would land in every split |
| Family split without stratification | Simpler | Small splits could end up with few trays of one species |

## R2. Near-duplicate families are merged before splitting

**Decision**: Hash one representative image per family (dHash, 64 bits) and merge families within Hamming distance 1 into one group (`DEDUP_MAX_DISTANCE = 1` in `manifest.py`). The limit is the largest distance at which the largest group holds at most 2% of families.

**Rationale**: Different file names can still be near-identical photos. On the 1,684 families, distance 1 gives 1,600 groups with the largest at 21 families (1.25%); distance 2 already chains 281 families (16.69%) into one group (evaluation record, "Near-duplicate threshold"). `tools/nn_leakage_check.py` then reports the nearest training neighbour of every validation and test family for inspection by eye.

**Alternatives considered**: Hash every variant at distance 4 (the first attempt; rejected: it chained 779 families, 46.26%, into one group, which the split then sent to validation). A stricter or looser distance (rejected by the 2% rule above). The record is explicit that the rule protects the split and is not a definition of a duplicate.

## R3. One image per family in validation and test

**Decision**: Training keeps every variant; validation and test keep one image per family: the published validation or test original if there is one, else the first colour variant by file name, else the first variant (`split.select_eval_variant`). The rule used is stored per image.

**Rationale**: Scoring several augmented copies of one tray would count that tray several times. The published valid/test originals are the only identifiable un-augmented photos. The record states the consequence plainly: most validation and test images are augmented variants (197 of 253 and 214 of 252).

**Alternatives considered**: Keep all variants in validation and test (rejected: inflates and correlates the score). Use only families that have an original (rejected: would shrink validation and test to 56 and 38 images).

## R4. Counting accuracy is the headline, beside mAP

**Decision**: The project reports, and gates on, both species-grouped mAP50 and per-photo count accuracy: a photo passes when each species' count is within ±10% of the truth, or within ±1 when the truth is below 10 (`metrics.count_accuracy`). Count accuracy is always shown with per-species count error, bias, exact-count rate, presence recall and error by density (`metrics.count_errors`).

**Rationale**: The apps show counts, not boxes. mAP uses every detection and measures ranking, so it says nothing about the threshold: run r18-1 reached species mAP50 0.835 on test while keeping no detection at 0.5. Count accuracy is what a learner sees. Its ±1 tolerance hides failures on photos with one insect, which is why the error measures sit beside it; about 46% of validation and test photos hold exactly one insect.

**Alternatives considered**: mAP alone (rejected for the reason above). Count error (MAE) alone (rejected as the gate: it has no pass/fail per photo; kept beside it).

## R5. The do-nothing baseline is always reported

**Decision**: Every count accuracy is reported beside the count accuracy of a model that finds nothing: 0.456 on test and 0.474 on validation. The app shows each model's validation count accuracy beside 0.474 (`docs/decisions.md`, 18 Oct).

**Rationale**: Because of the ±1 tolerance, finding nothing already passes on almost half the photos. r18-1's test count accuracy, 0.456, was exactly the baseline (115 of 252 photos); without the baseline beside it, that number looked like partial success.

**Alternatives considered**: Report it only when a model fails (rejected: the reader cannot tell a failure without it).

## R6. Threshold and calibration are chosen on validation

**Decision**: `tools/choose_demo_threshold.py` sweeps thresholds from 0.02 to 0.50 in steps of 0.02 on the validation split and picks the lowest total count error, preferring the higher threshold on ties. `tools/calibrate_scores.py` fits Platt scaling on validation detections and reports every count result out-of-fold, over 5 folds with photos grouped by family and the threshold re-chosen inside each fold. The test split is never read by either tool.

**Rationale**: A threshold tuned on the photos it is reported on is optimistic. Out-of-fold results show how stable the choice is: for r50-v5 the sweep chose 0.48 in four folds and 0.50 in one, giving out-of-fold count accuracy 0.834. Calibration also sets the review flag: for r50-v5, raw 0.64 maps to a calibrated 0.74, so `review_below` is 0.64.

**Alternatives considered**: Keep the specified 0.5 threshold (rejected after r18-1, whose scores never reached 0.25). Choose the threshold on test (rejected by Principle IV). Widen the grid after D-FINE-L chose its top value, 0.50, in four folds (rejected: the grid was fixed before the results; the possible cap is recorded instead).

## R7. Pre-registered rules and a budget for the test split

**Decision**: Before any wave-2 result, four rules were written down (evaluation record, "Wave 2"): A, r50-v5 replaces r50-1 only if it is better on crowded trays and its count accuracy is not lower; B, a challenger replaces r50-v5 only if its count accuracy is higher and it is better on crowded trays; C, the test look goes only to a model with out-of-fold validation count accuracy ≥ 0.80, the best such model, once; D, no model ships without ONNX ≤ 200 MB, parity on 10 validation photos and CPU time ≤ 5 s. Each test result is bound to the weights, manifest, annotations, threshold and evaluator version (`train.evaluation_id`, `check_cached_test`), and the notebooks' test cell refuses to run until a validation-chosen threshold is typed in.

**Rationale**: As the README states, the test split has had both its rule-based looks, r18-1 and then r50-v5, plus a post-hoc comparison of the two challengers, so a later model needs a new held-out set. Writing the rules first is what lets the test result mean anything.

**Alternatives considered**: Evaluate every model on test and pick the best (rejected: the choice would be fitted to the test split). Keep no test split and report validation only (rejected: validation is used for every choice and is optimistic).

## R8. Dense-tray paired bootstrap decides between close models

**Decision**: On the 18 validation photos with 30 or more white stemborers (one per family), pair two models' per-photo absolute errors and resample photos 10,000 times with seed `20261017`; a model is better only when the 95% interval of the mean difference lies entirely below 0.

**Rationale**: Crowded trays are the weakest case and the place where models differ most; a paired test on the same photos removes photo-to-photo variation. It was decisive twice: r50-1 over r18-1 (interval −7.56 to −0.44) and r50-v5 over r50-1 (−7.17 to −0.17).

**Alternatives considered**: Compare mean errors without an interval (rejected: 18 photos are too few to trust a raw difference). The README notes that this comparison was a one-off analysis with no tool in the repository; its method and results are in the evaluation record.

## R9. The denoising-loss bug and the move to transformers 5.20.1

**Decision**: Train wave 2 on `transformers` 5.20.1; pin it in the `train` extra with a comment, and keep 4.57.6 pinned only in the notebooks of the two earlier runs, which are kept for history.

**Rationale**: As recorded publicly in the evaluation record, `transformers` 4.57.6 computed RT-DETR's main loss over all decoder queries, including the 100 denoising queries; only the auxiliary outputs were split. Version 5.18.0 fixed this (PR #48528). With the same recipe and backbone, r50-v5's highest validation score rose from 0.31 to 0.94, its scores became close to calibrated (calibration error 0.046) and its count-optimal threshold moved from 0.04 to 0.48. The README puts it as the top validation score rising from 0.31 (r50-1) to 0.94 (r50-v5). The record marks the mechanism (matching targets to noised queries) as inferred, not measured.

**Alternatives considered**: Keep 4.57.6 and correct with calibration (tried on r18-1 and r50-1: calibration fixed what scores meant but count accuracy topped out at 0.632 and 0.751, below the 0.80 gate).

## R10. Model choice: r50-v5 over RF-DETR-M and D-FINE-L

**Decision**: r50-v5 (RT-DETR, ResNet-50-vd, 640 px, threshold 0.48) is the demo model. RF-DETR-M (576 px, 0.48) and D-FINE-L (640 px, 0.50) are published as comparison models.

**Rationale**: Under rule A, r50-v5 replaced r50-1. Under rule B, neither challenger replaced r50-v5: RF-DETR-M counted better on validation (0.846 against 0.834) but was not better on crowded trays (interval −0.72 to +3.11); D-FINE-L counted worse (0.822) and tied on crowded trays (−0.89 to +0.72). Rule C then gave the single test look to r50-v5: species mAP50 0.943, count accuracy 0.849, each sex class ≥ 0.798. The two challengers' later test figures (count accuracy 0.806 and 0.833) were computed post-hoc and played no part in the choice.

**Alternatives considered**:

| Model | For | Against |
| :-- | :-- | :-- |
| RF-DETR-M | Best validation count accuracy (0.846); smallest file (122.0 MB); 0.33 s per photo | Not better on crowded trays; needs a 576 px input |
| D-FINE-L | Fastest on CPU (0.14 s); best species mAP50 on validation (0.940) | Lower count accuracy; parity scores over 1e-3 (waived) |
| r50-1 (earlier run) | Already in use | Trained with the denoising-loss bug; count accuracy 0.751, below the gate |
| A YOLO-family baseline | The dataset's own benchmark uses it; the evaluation record suggested it as a comparison after r18-1 | Not run |

## R11. Training notebooks are generated, with a `--check`

**Decision**: `tools/build_notebook.py` writes each notebook from the package source and `data/`: every module is embedded with `%%writefile`, every data file as gzip plus base64, with fixed cell ids, a fixed gzip header and LF line endings, so the output is byte-reproducible. `--check` rebuilds into `runs/` and exits 1 if the committed notebook differs. Every notebook has the same 24 cells.

**Rationale**: One upload to Colab runs everything with no clone, no credentials and no drift between the notebook and the tested package. The check proves that the notebook that ran is the code in the repository; on 2026-10-19 all five committed notebooks matched a fresh build.

**Alternatives considered**: A hand-edited notebook that clones the repository (rejected: needs network access to the repository from Colab and lets the notebook drift from the code). Embedding only the code and downloading `data/` (rejected: one more network dependency).

## R12. Training-loop safeguards

**Decision**: Run the matcher and losses in float32 under fp16 autocast; skip updates with a non-finite gradient and stop after 50 in a row; store weights, score, epoch and experiment fingerprint in one atomically written `best.pt`; refuse to resume a run folder that holds a different experiment; restore all random state on resume (`train.py`).

**Rationale**: These came from an external review of the notebook on 2026-10-14 (evaluation record, "Review fixes"): in float16 the matcher's `log(p + 1e-8)` can produce infinite costs that the solver rejects; a resumed run must not mix experiments.

**Alternatives considered**: Turn mixed precision off (not chosen: the fix only needs the matcher and losses in float32). Ignore non-finite steps (rejected: it would hide a diverging run).

## R13. Export to ONNX, and parity by pairing

**Decision**: Export with `torch.onnx.export`, opset 17, static shapes, inside `eval()` and `no_grad()`, exposing only `logits` and `pred_boxes` (`tools/export_onnx.py`). For RF-DETR, the antialiased position-embedding resize is computed once eagerly and frozen into the graph. `parity()` pairs detections by class and highest box IoU, judges each photo on its own pairs and reports how many it compared. The parity sample is 10 validation photos at the operating threshold (rule D).

**Rationale**: An export traced outside inference mode froze input-dependent values; 0 of 300 output rows matched (evaluation record, ONNX export of r18-1). Pairing by position failed on CI when two runtimes broke near-ties differently; pairing by class and overlap removes that without loosening the tolerances (evaluation record, "Parity check pairs detections"). The record also notes that parity on the full test split, as first planned, has not been run; rule D sets the 10-photo validation sample as the gate.

**Alternatives considered**: TorchScript or a framework-specific format (rejected: the apps run ONNX Runtime). Order-based comparison (rejected for the reason above). Dynamic input shapes (rejected: the contract fixes S × S per model).

## R14. Data into Colab: one request, three pins

**Decision**: Download the dataset archive in a single request, check its size, MD5 and SHA-256 against pins in `fetch.py`, accept a copy on the user's own Google Drive verified the same way, extract only the files named in the split manifest and check each file's SHA-256.

**Rationale**: The record of the Zenodo listing gives size and MD5 only; the SHA-256 comes from an earlier measurement of a local copy whose size and MD5 matched (evaluation record, "Colab data path"). Nothing is redistributed by this step.

**Alternatives considered**: Commit the images or host a copy (not chosen: the README states that no images are redistributed; the notebooks download and verify them instead).

## R15. Publishing: manifests in the repository, weights on Kaggle

**Decision**: Publish the three ONNX files on Kaggle as one model with three variations (Apache-2.0, dataset credited), each holding `model.onnx`, `manifest.json` and its model card as `README.md`; keep only version 3 and pin the app to it. Keep `models/*.manifest.json` in the repository as the source of the app's catalogue (`docs/decisions.md`, 18 Oct).

**Rationale**: The weights are too large for the repository and the app needs a stable public download. Every manifest says `"validated": false`, and every card says teaching demo, not for farmers.

**Alternatives considered**: A GitHub release or a Hugging Face model repository (not chosen; the decision log records Kaggle as the host, and the app is pinned to its version 3 files). Committing weights (rejected: too large for the repository, as the decision log says).
