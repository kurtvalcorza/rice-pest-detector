---
license: apache-2.0
pipeline_tag: object-detection
base_model: Roboflow/rf-detr-medium
date_published: "2026-10-18"
---

# Rice-Pest Detector RF-DETR-M (RF-DETR medium)

[![Hugging Face: Roboflow/rf-detr-medium](https://img.shields.io/badge/%F0%9F%A4%97%20Hugging%20Face-Roboflow%2Frf--detr--medium-ffd21e)](https://huggingface.co/Roboflow/rf-detr-medium/tree/1b5b672408f86dd38e05dd3cf3f2e0834e545a59)
[![Upstream GitHub: roboflow/rf-detr](https://img.shields.io/badge/GitHub-roboflow%2Frf--detr-181717?logo=github)](https://github.com/roboflow/rf-detr)
[![arXiv: 2511.09554](https://img.shields.io/badge/arXiv-2511.09554-b31b1b)](https://arxiv.org/abs/2511.09554)
[![License: Apache-2.0](https://img.shields.io/badge/License-Apache--2.0-blue)](https://www.apache.org/licenses/LICENSE-2.0)

> **⚠️ Notice.** This model is for research, training and evaluation only. It is not validated for production, clinical, diagnostic or safety-critical use. It is not a field pest-surveillance or pest-alert system. Its counts are experimental estimates: they are not agronomic advice and must not be the basis for any pest-management or spraying decision. A qualified person should review them. Results in this card are tutorial evidence, not benchmarks. The model and this card are provided "as is", without warranty of any kind. To the maximum extent permitted by law, the maintainers accept no liability for their use.
>
> This is a teaching and demonstration model, made for the *Coding with AI Agents* workshop. It is not an official tool, product or service of any organisation or government agency, and no organisation endorses it. It is **not made for farmers** and has not been validated in the field.

#### Description

This model is RF-DETR at the medium size, fine-tuned from the Hugging Face checkpoint `Roboflow/rf-detr-medium` at revision `1b5b672408f86dd38e05dd3cf3f2e0834e545a59`. The upstream model page reports the checkpoint as trained on the COCO 2017 object detection label space. This card describes the fine-tuned model published as Kaggle version 3, identified as `rfdetr-m` in this repository.

RF-DETR is a real-time detector in the DETR family. The upstream authors describe a vision-transformer backbone in the style of DINOv2 with registers, alternating windowed and full attention. A projector passes its features to a multi-scale deformable decoder. The pinned `config.json` sets a 384-wide, 12-layer backbone with 16-pixel patches, 4 decoder layers and 300 object queries. The upstream authors report that the family's sizes were chosen by neural architecture search.

At inference time the model reads one 576×576 RGB image and returns 300 boxes with four class logits each. The caller applies a sigmoid, takes the maximum over the four classes as the score and keeps queries scoring at or above a threshold. Matching is one-to-one, so no non-maximum suppression is applied. Adaptation happened through supervised fine-tuning of the whole network on labelled light-trap photos. There is no in-context conditioning and no learning at inference time.

The upstream checkpoint supplies the architecture and pretrained weights; its COCO head was replaced by a new four-class head. This repository adds the rest:

- a family-grouped split of an open light-trap dataset, with COCO-format labels (`data/`);
- training code that generates the Colab notebook (`src/rice_pest_detector/train.py`, `tools/build_notebook.py`);
- the fine-tuned weights, exported to ONNX by `tools/export_onnx.py` and recorded by SHA-256 in `models/rice-pest-rfdetr-m.manifest.json`;
- evaluation, calibration and threshold tools (`src/rice_pest_detector/metrics.py`, `tools/calibrate_scores.py`, `tools/choose_demo_threshold.py`);
- the inference contract and its reference implementation (`docs/inference-contract.md`, `src/rice_pest_detector/infer.py`);
- a Flutter demonstration app for Android (`app/`), which can import this model and compare it with the default model, r50-v5.

#### Intended Use and Limitations

The model was built as a comparison detector for teaching how models are judged against each other, not to count pests for real decisions.

###### Primary Intended Uses

The task is object detection on a single photo of a light-trap tray. The input is one RGB image, resized to 576×576. The output is a list of boxes, each labelled as one of four classes (`RBB_FEMALE`, `RBB_MALE`, `WSB_FEMALE`, `WSB_MALE`) with a score. The demo app merges the sex classes and reports a count per species: rice black bug (*Scotinophara coarctata*) and white stemborer (*Scirpophaga innotata*).

The application domains envisioned during development are these:

- teaching, in the *Coding with AI Agents* workshop, how competing detectors are compared under rules fixed before the results;
- learning to build software that runs more than one model behind one inference contract, including models with different input sizes;
- research and comparison of detectors on this repository's family-grouped split of the Deleña et al. light-trap dataset.

The model's role is a challenger. It was trained with the same split and recipe as the default model, r50-v5, and judged against it under pre-registered rules. It did not replace r50-v5. In the demo app it is an optional model, which the app's compare screen can run beside the default on one photo.

###### Primary Intended Users

The intended users are participants in the *Coding with AI Agents* workshop and other learners building software with AI coding agents. Machine learning students and engineers studying detector comparison, and application developers studying on-device inference, are also intended users.

The deployment settings envisioned are teaching, self-study and research. A user may run the model on their own computer with ONNX Runtime, or import it into the demonstration app on their own Android phone or emulator. Neither setting involves real pest-management work.

The model assumes users who:

- know what an object detector, a confidence score and a counting threshold are, and that a count is an estimate with an error;
- can read mean average precision, mean absolute error and calibration error, and can follow `docs/evaluation-record.md`;
- can run Python 3.12 or the Flutter toolchain, and can check a file's SHA-256 before use;
- understand that the model has seen only light-trap photos from one dataset, and that it is not robust to other photos.

The model is not built for farmers, extension workers or pest-control operators, and assumes no agronomic expertise of its users.

###### Out-of-scope use cases

The model is not for the uses below.

- **Capability: other species.** It detects only rice black bug and white stemborer. Any other insect on a tray is either missed or miscounted as one of these two species.
- **Capability: reporting by sex.** The four classes separate female and male, but the app reports species only. Sex-class figures are evaluation evidence, not an output to rely on.
- **Capability: tasks other than box detection.** The model does not segment insects, measure their size, track them across frames or classify a whole tray as pest-free. The training data contains no pest-free images, so behaviour on empty trays is not measured.
- **Capability: replacing the default model.** It is not the demo app's default and did not meet the rule for replacing it. Use r50-v5 where one model must be chosen.
- **Input: other photos.** Do not use it on photos from other trap designs, cameras, crops or regions, or on phone photos taken in the field. Performance on such photos is not measured, and no field validation set exists.
- **Input: image size and shape.** The model takes exactly `(1, 3, 576, 576)`, not the 640×640 of the other models. Every photo is resized to 576×576 without keeping its aspect ratio, so non-square photos are stretched. The demo app rejects photos smaller than 32 pixels on a side.
- **Input: crowded trays.** Do not use counts from trays with more than 30 insects without review. Crowded trays have the largest errors, and the app flags photos with more than 30 counted insects. The model cannot return more than 300 detections per photo.
- **Decision: pest management.** Do not use it for any pest-management, spraying or treatment decision. No such use is admissible without field validation and expert review of every count.
- **Decision: unattended use.** Do not use its counts without a person reviewing them, and do not use it as a field tool or a surveillance system.
- **Decision: official use.** Do not use it in any official or institutional role, or in any way that implies an organisation endorses it.

#### Factors

The factors considered during development are insect classes and tray density, the capture of the dataset's photos, and the compute and data conditions under which the reported figures hold.

###### Groups

The model is not human-centric. Its inputs are photos of insects on light-trap trays, and its four output classes are insect species and sex. No person is a data subject of the task, so demographic or phenotypic groups of people do not apply to its outputs.

The categories of data instance that this repository did evaluate are the four insect classes and the density of insects per photo. Per-class mAP50 and white stemborer error on trays with 30 or more insects are reported under Performance Measures. Crowded trays are the weakest case.

The upstream checkpoint was trained in the COCO 2017 label space, and COCO contains photos of people. This repository has not audited the upstream training data by group, and the upstream model page does not report a group audit. The COCO head was replaced, and the fine-tuned model has no person class.

No audit by region, trap type, camera, season or pest population was possible, because the dataset leaves its capture date, location and trap fields blank. An operator who uses the model on their own photos is expected to perform that audit: label a sample of their own photos and compare `count_errors` across regions, trap types, cameras and densities before relying on any count.

###### Instrumentation

The data comes from light traps whose trays were photographed. The training and evaluation photos are from the Deleña et al. dataset on Zenodo (doi:10.5281/zenodo.20066074). The dataset does not document the camera, lens, lighting or capture procedure.

The characteristics that materially affect the data are these:

- every image was pre-stretched to 640×640 before release, so the original resolution and aspect ratio are lost; this model then resizes each image again, to 576×576;
- the photos are exports with augmented variants: one original photo and its variants form a family, and some variants are greyscale;
- capture date, location and trap fields are blank in all metadata rows;
- the annotations are not documented as human-verified;
- 652 label files contained polygon rows, which this repository converted to bounding boxes (`data/README.md`);
- a scan of all 5,453 images used found every image at 640×640 with no EXIF rotation tag.

Instrument error reaches the model as image error. A different camera, focus, exposure, white balance or tray background shifts the pixel distribution away from the training photos. Label errors in the dataset reach the model as training noise and reach the evaluation as wrong reference counts. The repository cannot detect any of these at inference time: it has no out-of-distribution check. The app's review flags react only to low scores and crowding, which is an indirect signal at best.

###### Environment

**Operating environment.** The distributed form is an ONNX file at opset 17, with float32 input `pixel_values` of shape `(1, 3, 576, 576)`. It was checked on CPU with ONNX Runtime's `CPUExecutionProvider`. The repository was last tested with `onnxruntime` 1.31.0. The demo app runs imported models with ONNX Runtime 1.28.0 on Android through `flutter_onnxruntime` 1.9.0, resizing to the manifest's `input_size`. No GPU is needed for inference.

Measured by this repository: the median CPU time per photo was 0.33 s, over 10 photos on one laptop. The laptop's CPU model is not recorded in `docs/evaluation-record.md`. Latency on a phone has not been measured, and memory use has not been measured on any device. Training needs a CUDA GPU: the notebook stops if none is attached, and it ran on a Colab T4.

**Data environment.** The reported figures hold for light-trap tray photos like those in the dataset. The validation and test splits are family-grouped holdouts from the same dataset, so they measure performance on new photos of the same kind, not on a new kind of photo. The repository assumes inference photos come from the same distribution: similar trays, lighting, insect sizes and image preparation.

Degradation when that assumption fails is not measured: other traps, cameras, crops, regions, seasons, lighting and phone photos taken in the field are all untested. Within the dataset, accuracy degrades with crowding: white stemborer error on trays with 30 or more insects is several times the per-photo average error.

#### Metrics

The measures were chosen because the app's output is a count per species, while detection quality and score meaning determine whether that count can be trusted.

###### Performance Measures

The repository reports these measures. Names are the keys the code writes.

- `map50_species` (`evaluate` in `src/rice_pest_detector/train.py`): mean average precision at IoU 0.50 with female and male merged into species, via pycocotools with `maxDets = [1, 10, 300]`. It measures ranking quality over all detections, independent of the counting threshold.
- `map50_by_class`: the same at four classes, with `all` and one value per class (`RBB_FEMALE`, `RBB_MALE`, `WSB_FEMALE`, `WSB_MALE`).
- `count_accuracy` (`src/rice_pest_detector/metrics.py`): the share of photos where both species' counts are within ±1 of the truth when the true count is below 10, or within ±10% otherwise. It measures discrete counting correctness at the threshold.
- `count_accuracy_no_detection_baseline`: the same measure for predicting zero insects everywhere.
- `count_errors`: per species, `mae` (mean absolute error), `bias` (mean signed error; negative is an undercount), `exact` (share counted exactly), `presence_recall` and `mae_by_density` (bins `1-9`, `10-29`, `30+`).
- `confusion`, `detections_kept` and `top_score_per_image`, reported by `evaluate` beside the others.
- `ece` (`tools/calibrate_scores.py`): expected calibration error over 10 equal-width bins, which measures how well raw scores match observed precision.

Each measure covers a gap in the others. mAP alone would hide a threshold that counts nothing, because it ignores the threshold. Count accuracy alone overstates skill, because about 46% of validation and test photos hold exactly one insect and pass at ±1 when nothing is detected; the baseline exposes that. MAE and bias give the size and direction of the error, and the density bins show where counting fails. ECE matters because the app's review flag reads a raw score as a probability.

Results, measured by this repository. Validation counts are out-of-fold (see Approaches to uncertainty and variability). The test column is a post-hoc evaluation at the project owner's request, made after the demo model had been chosen and after r50-v5's pre-registered test evaluation. It is for comparison only and was **not** used to select any model.

| Measure | Test, 252 photos, post-hoc, threshold 0.48 | Validation, 253 photos |
| :-- | --: | --: |
| `map50_species` | 0.944 | 0.933 (best epoch) |
| `map50_by_class` `all` | 0.853 | 0.837 (best epoch) |
| `RBB_FEMALE` / `RBB_MALE` / `WSB_FEMALE` / `WSB_MALE` | 0.891 / 0.783 / 0.852 / 0.887 | 0.900 / 0.787 / 0.785 / 0.876 |
| `count_accuracy` | 0.806 | 0.846 (out-of-fold) |
| `count_accuracy_no_detection_baseline` | 0.456 | 0.474 |
| `mae`, RBB / WSB | 0.58 / 1.08 | 0.28 / 1.38 (out-of-fold) |
| `bias`, RBB / WSB | +0.44 / −0.04 | not recorded |
| `exact`, RBB / WSB | 84% / 68% | not recorded |
| WSB `mae_by_density` `30+` | 4.57 (23 photos) | 9.56 (18 photos) |
| RBB `mae_by_density` `30+` | 5.00 (17 photos) | not recorded |
| `ece`, raw scores | not measured | 0.035 |
| Highest top score on any photo | not recorded | 0.9485 |

Presence recall, the other density bins and the confusion counts are not recorded in `docs/evaluation-record.md` for this model. It counted best of three models on validation and worst on test; see Approaches to uncertainty and variability.

###### Decision thresholds

**The default decision rule.** Each query's score is the sigmoid of its logit, computed in float64, taking the maximum over the four classes. The predicted class is the argmax over the four classes. The max and the argmax are implicit decision rules: a query never carries two classes. Female and male classes are then merged into species for counting. A query is kept if its score is at or above the threshold; the comparison is inclusive. The model applies no non-maximum suppression. The contract's default threshold is 0.50 when a caller passes none (`src/rice_pest_detector/infer.py`).

**The counting threshold, 0.48.** `models/rice-pest-rfdetr-m.manifest.json` sets `threshold` to 0.48. `tools/choose_demo_threshold.py` chooses the value with the lowest total count error on validation, on a grid from 0.02 to 0.50 in steps of 0.02, preferring the higher threshold on ties. Inside 5 family-grouped folds the chosen values ranged from 0.44 to 0.48, so none lay at the top of the grid.

**The review flags.** The app flags a photo when any counted detection scores below `review_below`, 0.63 for this model. That is the raw score whose Platt-calibrated probability on validation is about 0.74, the same meaning as the default model's flag. The Platt parameters for this model are not recorded in `docs/evaluation-record.md`. The app also flags any photo with more than 30 counted insects (`crowdedAbove` in `app/lib/counting/counting.dart`); this limit is the same for every model.

**Acceptance thresholds set during development.** The design spec (`docs/specs/2026-10-13-rice-pest-detector-design.md`) set the quality gates before training: `map50_species` ≥ 0.80, `count_accuracy` ≥ 0.80, and each sex class ≥ 0.70 before sex classes may be shown. It also set ship gates: ONNX ≤ 200 MB, CPU time ≤ 5 s per photo and parity with PyTorch (same kept detections, box IoU ≥ 0.99, score difference ≤ 1e-3). These are quality bars for a teaching demo, chosen before any result. They are not agronomic action thresholds, and no target domain imposed them. This model meets the ship gates and, on validation and on the post-hoc test, the quality gates.

**The replacement rule.** A challenger could replace the default model only if its out-of-fold count accuracy beat r50-v5's and the 95% bootstrap interval of its dense-tray error difference lay entirely below 0. This model's count accuracy was higher (0.846 against 0.834), but its interval was [−0.72, +3.11], so it did not replace r50-v5.

**Thresholds left to the caller.** Anyone who sets their own threshold owns that choice. Lowering it keeps more detections, which reduces missed pests and adds false alarms. Raising it does the opposite. A missed pest leads to an undercount, which could delay attention to a real infestation. A false alarm leads to an overcount, which could prompt needless concern or pesticide use. Weigh those two costs for your own setting. Then choose the threshold on your own labelled photos with `tools/choose_demo_threshold.py` or a cost-weighted variant, never on the photos you report results on. Keep `review_below` at or above the threshold; the app's manifest parser enforces this. No threshold makes the model fit for a spraying decision.

###### Approaches to uncertainty and variability

**Estimation procedures.** Every figure comes from one training run of one model, with one seed (`20261013`). No run was repeated, so no seed-to-seed variance has been measured. The checkpoint was chosen as the epoch with the highest validation `map50_species` over 40 epochs (epoch 3, counting from 0). That selection makes the validation mAP slightly optimistic.

Validation counts are out-of-fold. The 253 validation photos were split into 5 folds grouped by family (fold seed `20261016`). For each fold, the threshold and the Platt fit were chosen on the other four folds and applied to the held-out fold.

The test figures come from one post-hoc evaluation of 252 photos at threshold 0.48. It went beyond the pre-registered rule, which allowed one test evaluation for one model, and that evaluation went to r50-v5. This test split had already been evaluated twice for other models.

**Dispersion.** No confidence interval is reported for mAP, count accuracy or MAE. The only interval is from a paired bootstrap on the 18 validation photos with 30 or more white stemborers: 10,000 resamples of photos, seed `20261017`. Against r50-v5, the mean paired difference in white stemborer absolute error (this model minus r50-v5) was +0.89, with a 95% interval of [−0.72, +3.11]. This model was better on 6 of those photos and worse on 7.

Differences of a few points between the three fine-tuned models are within run-to-run and split-to-split variation. This model counted best on validation (0.846) and worst of the three on test (0.806).

**Sources of variability.** The seed fixes Python, NumPy and PyTorch random state, and the data-loader shuffle uses seed plus epoch. Random state is restored on resume. Not controlled: non-deterministic CUDA kernels, float16 autocast and the GPU type. The new class head is randomly initialised from the seed. ONNX and PyTorch differ slightly in numerics: up to 5.1e-6 in score at the operating threshold.

**Confidence outputs.** The score is a sigmoid output, not a calibrated probability. On validation its expected calibration error was 0.035, so raw scores are close to calibrated on these photos. The app uses raw scores and does not apply a calibration. To obtain calibrated probabilities on other photos, label a sample and fit Platt scaling with `tools/calibrate_scores.py`.

#### Ethical considerations and biases

No external ethics board reviewed this model, and it was not tested with any group of users for clearance.

###### Data

**Pretraining.** The upstream model page reports `Roboflow/rf-detr-medium` as trained in the COCO 2017 object detection label space (80 categories). COCO is a corpus of everyday photos that includes many photos of people. The model page does not enumerate any further pretraining data, such as data used for the backbone, and the disclosure ends there. Sensitive or personal content in the pretraining data is therefore not ruled out.

**Fine-tuning.** The model was fine-tuned on the Deleña et al. light-trap dataset (Zenodo, doi:10.5281/zenodo.20066074, CC BY 4.0). The split used 4,948 training, 253 validation and 252 test photos. The photos show insects on trap trays and are not intended to contain people. Their capture metadata is blank. This repository did not audit every image for incidental personal content, so it is not known to contain none; no such content was observed.

**What this repository distributes.** It distributes code, the split manifest, COCO-format labels derived from the dataset, generated notebooks and model manifests with SHA-256 digests. It does not distribute images: the notebooks download the archive from Zenodo and check every image. It does not contain the model weights: ONNX and PyTorch files are excluded from version control. The ONNX file is published on Kaggle at [https://www.kaggle.com/models/kurtvalcorza/rice-pest-detector/Onnx/rf-detr-m](https://www.kaggle.com/models/kurtvalcorza/rice-pest-detector/Onnx/rf-detr-m), with a manifest and a copy of this card. The PyTorch checkpoint is not distributed.

**Operator obligation.** Photos supplied at inference may contain people, faces or location data in their EXIF fields. The model does not check for any of these. The demo app keeps photos and history in the app's own storage on the phone and makes no network call except an explicit model download. Before sharing photos or counts, the operator must check them for personal, sensitive or proprietary content.

###### Human Life

The model is not intended for decisions in health, safety, criminal justice, employment, credit, housing or any other domain central to human life. It is a teaching model.

Its domain still bears on livelihoods. Pest-management decisions affect crop losses, farm income, pesticide use and the exposure of people and the environment to pesticides. The model has not been validated or certified for any such decision, by anyone. Its only validation is this repository's evaluation on held-out photos from the same dataset. No field validation, agronomic review or regulatory clearance has taken place.

Use by farmers or extension services is foreseeable, though not intended. It would be admissible only under all of these conditions:

- a field validation set of local photos, labelled by entomologists or other trained annotators;
- independent review of the results by agricultural experts;
- a qualified person reviewing every count before it informs anything;
- compliance with local pest-management and pesticide regulations.

###### Mitigations

Each mitigation below is implemented in this repository and can be inspected.

**Supply-chain integrity.**

- The notebook pins the base checkpoint: `TrainConfig(base_model="Roboflow/rf-detr-medium", revision="1b5b672408f86dd38e05dd3cf3f2e0834e545a59", …)` in `notebooks/train_colab_rfdetr-m.ipynb`. The notebook also pins `transformers==5.20.1`.
- The notebook checks the Zenodo archive's size, MD5 and SHA-256, and every image against `data/split_manifest.json`, before training.
- `models/rice-pest-rfdetr-m.manifest.json` records the ONNX file's SHA-256 and size. The app installs a model only if both match, and re-checks the size and SHA-256 when it loads a model. A stamp from an earlier successful check lets it skip the hash only while the file's size and modification time are unchanged.
- The app identifies the default model by its SHA-256, so this model's manifest cannot claim the default's id to avoid the not-validated banner.

**Input integrity.**

- The app's manifest parser rejects unknown, missing or out-of-range fields. It requires `input_size` from 320 to 1280, a `threshold` above 0.02 and a `review_below` not under the threshold.
- Importing a model checks size, SHA-256, the ONNX input and output names and shapes at the manifest's `input_size`, and a self-test on a synthetic image that must give finite outputs of the right shape. On any failure the app deletes the copies, says why and keeps the current model.
- Inputs follow `docs/inference-contract.md`: EXIF orientation applied first, conversion to RGB, bilinear resize to 576×576. The app rejects photos under 32 pixels a side.
- Label validation (`src/rice_pest_detector/labels.py`) rejects class ids outside 0–3, boxes outside the image, zero areas and non-finite coordinates. A family with an invalid label is excluded and logged in `data/exclusions.json`.

**Statistical mitigations.**

- Splits are grouped by family, and near-duplicate families (dHash distance ≤ 1) are grouped before splitting. No family or duplicate group appears in more than one split. Validation and test keep one photo per family.
- Threshold and calibration are chosen out-of-fold on validation only. The test split is never read during training or threshold choice.
- The rules for choosing the demo model and for spending the test evaluation were fixed in writing before any result they judged (`docs/evaluation-record.md`). This model's test result was computed after the choice and is labelled post-hoc.
- The notebook's test cell refuses to run while `THRESHOLD = None`. `check_cached_test` refuses a cached test result unless its weights, manifest, annotations, threshold and evaluator version all match.
- No class balancing or re-weighting was applied.

**Reproducibility.**

- The seed `20261013` is fixed, and `last.pt` stores an experiment fingerprint; resuming refuses a run folder from a different experiment.
- Notebooks are generated by `tools/build_notebook.py`, whose `--check` mode confirms the committed file matches the source.
- ONNX output was compared with PyTorch by `parity` in `tools/export_onnx.py` (see Verification records).

**Refusals.**

- The app reports species only and does not show sex classes.
- The app gives no treatment or spray advice. The test `no string gives treatment or spray advice` in `app/test/l10n_test.dart` fails if any string suggests one.
- The manifest declares `"validated": false`. Because this is not the default model, the app shows a "not validated" banner on the home screen, on its results, in the compare screen and in shared summaries.

###### Risks and harms

- **Miscounting crowded trays.** On trays with 30 or more white stemborers, mean absolute error was 4.57 per photo on test and 9.56 on validation. On trays with 30 or more rice black bugs it was 5.00 on test. Such trays were 23 and 17 of 252 test photos. The operator, and anyone acting on the count, bears the harm. Misused for decisions, a miscount could misstate an infestation. The crowded-tray flag reduces but does not remove this risk.
- **Instability between splits.** Count accuracy fell from 0.846 on validation to 0.806 on test. A reader who picked this model on validation alone would have overrated it. Its counting skill relative to the other models is not established.
- **Out-of-distribution photos.** On photos unlike the dataset, the model can return confident detections that are wrong, such as other insects counted as rice black bug. It has no out-of-distribution check, and behaviour on empty trays is unmeasured. Every untested photo source carries this risk, and its size is unknown.
- **Overconfidence.** The calibration holds for validation photos only. On other photos, a score of 0.63 may not mean a 74% chance of a real insect, so the review flag can miss doubtful counts.
- **Automation bias.** A clean-looking count invites trust. Users may accept counts without checking, especially on photos without a flag. Unflagged photos are not guaranteed correct.
- **Misuse as an official or advisory tool.** Presenting counts as surveillance data or as a basis for spraying could lead to needless or missed pesticide use. Farmers, consumers and the environment would bear that harm.
- **Undetected leakage.** Deduplication stops at Hamming distance 1. 42 test families lie within distance 2 of a training family, and three close test pairs have not been inspected by eye. Remaining near-duplicates would make the test figures optimistic.
- **Reused test split.** The test split had been evaluated twice before this model's post-hoc evaluation. Its test figures are comparison evidence, not an unbiased estimate.
- **Bias from the data.** The dataset's regions, seasons and trap types are undocumented. Any skew in them passes into the model unmeasured. Users in places unlike the source bear the resulting error.

###### Use cases

These uses are unacceptable even where the model would work:

- presenting its counts as official pest surveillance, pest alerts or agronomic advice;
- using its counts to justify, schedule or dose a pesticide application or spraying;
- implying that any organisation or government agency endorses, operates or validated it;
- marketing or supplying it to farmers as a validated tool;
- deceptive applications, such as publishing its counts as survey data without saying they are unvalidated model estimates.

Surveillance of people, biometric or demographic profiling and social scoring do not apply in the usual sense. The model detects only four insect classes and makes no inference about people. Using it on photos of people is out of scope, and its outputs would be meaningless there.

Unlawful discrimination in employment, housing, credit, insurance, education or healthcare does not apply, because the model makes no decision about any person.

The Apache-2.0 licence of the upstream weights permits broad use and adds no use prohibition. Its notice and attribution terms apply. Use of the fine-tuning data requires attribution under CC BY 4.0.

---

## Model files and digests

| Item | Value |
| :-- | :-- |
| ONNX file | `rice-pest-rfdetr-m.onnx` |
| Size | 121,956,743 bytes (122.0 MB) |
| SHA-256 | `07161f11d2bfc390510627ddff72a8436045b1f79cccd00682f19359fe5c660f` |
| Opset | 17 |
| Manifest | [`models/rice-pest-rfdetr-m.manifest.json`](../../models/rice-pest-rfdetr-m.manifest.json) |
| Source checkpoint | `best.pt`, SHA-256 beginning `5122c68a`, epoch 3 (counting from 0); not distributed |
| Base model | `Roboflow/rf-detr-medium` at `1b5b672408f86dd38e05dd3cf3f2e0834e545a59` |

Check the file before use, for example with `sha256sum rice-pest-rfdetr-m.onnx` or `Get-FileHash rice-pest-rfdetr-m.onnx -Algorithm SHA256`. Do not use a file whose digest or size differs.

## Input and output contract

The full contract is [`docs/inference-contract.md`](../inference-contract.md); the reference implementation is [`src/rice_pest_detector/infer.py`](../../src/rice_pest_detector/infer.py).

| Tensor | Shape | Content |
| :-- | :-- | :-- |
| `pixel_values` (input) | `(1, 3, 576, 576)`, float32 | RGB, EXIF orientation applied, bilinear resize to 576×576, divided by 255, no mean or standard-deviation normalisation |
| `logits` (output) | `(1, 300, 4)` | raw class logits per query, before the sigmoid |
| `pred_boxes` (output) | `(1, 300, 4)` | normalised `cx, cy, w, h` per query |

Class ids: 0 `RBB_FEMALE`, 1 `RBB_MALE`, 2 `WSB_FEMALE`, 3 `WSB_MALE`. Classes 0 and 1 count as rice black bug; 2 and 3 as white stemborer. Convert boxes with the width and height of the image after EXIF rotation.

## Training configuration

| Setting | Value |
| :-- | :-- |
| Notebook | [`notebooks/train_colab_rfdetr-m.ipynb`](../../notebooks/train_colab_rfdetr-m.ipynb), generated by `tools/build_notebook.py --revision 1b5b672408f86dd38e05dd3cf3f2e0834e545a59 --variant rfdetr-m` |
| Library | `transformers==5.20.1` |
| Input | 576×576 (`input_size=576`), the size of the upstream configuration |
| Head | new 4-class head, `num_queries` 300 |
| Optimiser | AdamW, learning rate 1e-4, 1e-5 for parameters whose names contain `backbone`, weight decay 1e-4 |
| Schedule | cosine annealing over 40 epochs, batch 4, gradient clipping at 0.1 |
| Precision | float16 autocast, with the matcher and losses in float32; updates with a non-finite gradient are skipped |
| Seed | `20261013` |
| Augmentation | none online; the training split keeps every augmented variant the dataset supplies |
| Checkpoint selection | highest validation `map50_species`; best at epoch 3 of 0–39 |

## Using the model with the demo app

The app's documentation is in the [README](../../README.md#demo-app-android). This is not the default model, so the app marks its counts as not validated.

1. Obtain `rice-pest-rfdetr-m.onnx` and check its SHA-256 and size against the table above.
2. In the app, open Settings, then Model, then "Import a model from a file".
3. Pick `models/rice-pest-rfdetr-m.manifest.json`, then the `.onnx` file. The app enables the model only if every import check passes.
4. Use "Compare models on one photo" to see its counts beside the default model's. Expect species counts, review flags and the not-validated banner but no advice.

## Verification records

Each record below is one execution, as recorded in [`docs/evaluation-record.md`](../evaluation-record.md). The run artefacts it cites (executed notebooks, checkpoints, result files) are not part of the public repository, so these records cannot be reproduced exactly without them; the exported ONNX files are published on Kaggle.

**Training run**

- **Date:** 2026-10-17
- **Subject:** `notebooks/train_colab_rfdetr-m.ipynb`, the committed notebook run unchanged. The evaluation record does not name the exact git revision executed.
- **Runtime:** Google Colab, NVIDIA T4 GPU, `transformers==5.20.1` as pinned in the notebook. Python and PyTorch versions are not recorded in the evaluation record.
- **Procedure:** all cells run through the Colab command-line interface; batch 4, 40 epochs at 576×576; the last cell stopped at the locked test cell, as designed.
- **Observed result:** 21,108 s wall clock (5.9 h); best validation `map50_species` 0.933 at epoch 3, four-class 0.837; 0.891 at epoch 39; highest validation score on any photo 0.9485; `best.pt` SHA-256 beginning `5122c68a`.
- **Caveats:** one run with one seed; the validation mAP is the maximum over 40 epochs and so slightly optimistic.

**Validation analysis**

- **Date:** 2026-10-17
- **Subject:** `rice-pest-rfdetr-m.onnx` (SHA-256 `07161f11…`) with `tools/calibrate_scores.py` and `tools/choose_demo_threshold.py`
- **Runtime:** CPU, ONNX Runtime `CPUExecutionProvider`; version not recorded
- **Procedure:** all 253 validation photos; Platt fit; 5 family-grouped folds with the threshold re-chosen inside each fold; paired bootstrap on the 18 dense photos against r50-v5
- **Observed result:** out-of-fold `count_accuracy` 0.846; MAE RBB 0.28, WSB 1.38; WSB `30+` MAE 9.56; raw `ece` 0.035; fold thresholds 0.44–0.48; bootstrap difference +0.89, 95% interval [−0.72, +3.11]
- **Caveats:** validation only

**Test evaluation (post-hoc, comparison only)**

- **Date:** 2026-10-18
- **Subject:** the PyTorch checkpoint (`best.pt` beginning `5122c68a`) with `evaluate` from `src/rice_pest_detector/train.py`, the same code as r50-v5's test evaluation
- **Runtime:** local CPU; library versions are not recorded in the evaluation record
- **Procedure:** after the demo model was fixed and after r50-v5's test evaluation, at the project owner's request; the 252 test photos evaluated once at 576×576 and threshold 0.48; the result file is marked as a post-hoc exception
- **Observed result:** `map50_species` 0.944; `count_accuracy` 0.806 (baseline 0.456); sex classes 0.891 / 0.783 / 0.852 / 0.887; further figures under Performance Measures
- **Caveats:** not used to select any model; the test split had been evaluated twice before; run on the PyTorch checkpoint, not the ONNX file

**ONNX parity and CPU latency**

- **Date:** 2026-10-17
- **Subject:** `rice-pest-rfdetr-m.onnx` (SHA-256 `07161f11…`) against the PyTorch checkpoint, with `parity` in `tools/export_onnx.py`
- **Runtime:** CPU, ONNX Runtime `CPUExecutionProvider`; version and CPU model not recorded
- **Procedure:** 10 validation photos at the operating threshold 0.48; a second, query-by-query comparison at 0.04; CPU time as the median over 10 photos
- **Observed result:** at 0.48, 127 detections compared, maximum score difference 5.1e-6, minimum box IoU 0.99999, 0 failures; at 0.04, all 717 queries matched; median CPU time 0.33 s per photo
- **Caveats:** 10 photos, not the full test split; one laptop; no phone measured

## Citation

Dataset: Deleña, R.; Balleras, G.; Dequiña, B. J.; Jumawan, R.; Flores, C. *Annotated light-trap rice pest image dataset with detector-derived region-of-interest crops for species-sex recognition of rice black bug and white stemborer.* Version 1. Zenodo. [doi:10.5281/zenodo.20066074](https://doi.org/10.5281/zenodo.20066074). Licence: [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).

Upstream model: Robinson et al. *RF-DETR: Neural Architecture Search for Real-Time Detection Transformers.* [arXiv:2511.09554](https://arxiv.org/abs/2511.09554). Weights: [`Roboflow/rf-detr-medium`](https://huggingface.co/Roboflow/rf-detr-medium/tree/1b5b672408f86dd38e05dd3cf3f2e0834e545a59), Apache-2.0.

Repository code is licensed Apache-2.0 (`LICENSE`); third-party notices are in `NOTICE`.
