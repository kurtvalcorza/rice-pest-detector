# Feature Specification: Rice-Pest Model Training

**Feature Branch**: `001-model-training`

**Created**: 2026-10-19

**Status**: Implemented (Spec Kit record written 2026-10-19; the pipeline was first designed with a brainstorming workflow before Spec Kit was added to this repository)

**Input**: User description: "A CPU-friendly object detector that counts rice black bug and white stemborer in light-trap photos, trained on the open dataset by its authors (Deleña et al.), with leakage-free splits, pre-registered quality gates judged on held-out data, an exported model that runs on a laptop CPU and a phone, and published weights for teaching only."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Split the open dataset without leakage (Priority: P1)

A maintainer takes the open light-trap dataset by its authors (Deleña et al.) and turns it into training, validation and test sets in which no photo, no augmented copy of a photo and no near-identical photo appears on both sides of a split, so that every later score measures new photos rather than remembered ones.

**Why this priority**: Every number this project reports depends on the held-out photos being truly held out. The published split of the dataset lets copies of one tray sit in training and test, so it cannot be used as it is. Nothing else is worth building until the split is right.

**Independent Test**: Rebuild the split from the downloaded dataset and confirm that the result is identical to the committed one, that no family, near-duplicate group or identical file appears in two splits, and that the split sizes match the record.

**Acceptance Scenarios**:

1. **Given** the downloaded dataset, **When** the split is built, **Then** each original photo and its augmented variants (a "family") end up in exactly one split, and families that are near-identical to each other are kept together.
2. **Given** a label file with a box outside the image, a box with no area, an unknown class, a non-finite coordinate, a malformed row or no label file at all, **When** the split is built, **Then** that whole family is excluded and the reason is written to an exclusions list.
3. **Given** a label row that outlines an insect as a polygon instead of a box, **When** the split is built, **Then** it is converted to the smallest box around the polygon.
4. **Given** the built split, **When** a reader opens it, **Then** each image has its family, group, split, source path in the dataset archive, size, dimensions, checksum and boxes, and no image itself is stored in the repository.
5. **Given** the same dataset and the same seed, **When** the split is built twice, **Then** both results are identical.

---

### User Story 2 - Train a detector reproducibly on a free cloud GPU (Priority: P2)

A maintainer or a workshop participant opens a training notebook on a free cloud GPU, chooses "run all", and gets a trained checkpoint, chosen on validation only, that survives a disconnect and can be traced back to the exact code, data and settings that produced it.

**Why this priority**: A model is the point of the project, but it is only worth judging if it was trained on the leakage-free split (Story 1) by a process that cannot quietly change between runs.

**Independent Test**: Regenerate a notebook from the repository's source and confirm it is byte-identical to the committed one; run the training loop on a few images on a CPU and confirm that it writes a history, a latest checkpoint and a best checkpoint, and that it resumes after being stopped.

**Acceptance Scenarios**:

1. **Given** a notebook generated from the repository, **When** it runs, **Then** it downloads the dataset in one request, checks the archive's size and two checksums, extracts only the images in the split, checks every image's checksum, and stops with a clear message on any mismatch.
2. **Given** no GPU is attached, **When** the notebook starts, **Then** it stops before installing or training and says how to attach one.
3. **Given** a session that disconnects mid-training, **When** the user runs all again, **Then** training resumes from the last saved epoch with the same random state; **When** the run folder holds a different experiment (other settings, split or validation labels), **Then** it refuses to resume and names what changed.
4. **Given** a training step whose loss or gradient is not a finite number, **When** it happens, **Then** that update is skipped and counted; **When** it keeps happening, **Then** training stops and says it diverged.
5. **Given** training is running, **When** an epoch ends, **Then** the best checkpoint is chosen on validation detection quality only, and the test photos are never read.

---

### User Story 3 - Judge a model by rules fixed before the results (Priority: P3)

The maintainer decides whether a trained model is good enough, and which of several models to use, by rules written down before any result is seen, using validation photos for every choice and the test photos only for a single, pre-agreed look.

**Why this priority**: Without it, a model is chosen by whichever number looks best, and the test score stops meaning anything. It builds on a trained model (Story 2) but can be tested on any saved set of detections.

**Independent Test**: Run the threshold choice and calibration on a saved set of validation detections and confirm that the threshold and the out-of-fold counts are reproduced; confirm that a cached test result is refused when the model, the split, the labels, the threshold or the evaluator has changed since it was made.

**Acceptance Scenarios**:

1. **Given** a trained model, **When** it is evaluated, **Then** the report gives species-level detection quality, detection quality for each sex class, count accuracy, and beside it the count accuracy of a model that finds nothing, plus count error, bias, exact-count rate and presence recall per species, by tray density.
2. **Given** validation detections, **When** a counting threshold is chosen, **Then** it is the threshold with the lowest total count error on a fixed grid, the higher one on a tie, and its count accuracy is reported out-of-fold with photos grouped by family.
3. **Given** two models, **When** they are compared on crowded trays, **Then** one counts as better only when a paired resampling of its per-photo errors shows the whole 95% interval of the difference below zero.
4. **Given** the test split, **When** a model is to be evaluated on it, **Then** this happens only under a rule written down beforehand, at a threshold already fixed on validation, and the result is tied to the exact model, split, labels, threshold and evaluator; a second run gives back the cached result instead of looking again.
5. **Given** any reported number, **When** a reader looks for its source, **Then** the evaluation record gives the run, the split, the date and the file it came from.

---

### User Story 4 - Export a model that runs on a laptop CPU and a phone (Priority: P4)

The maintainer turns a chosen checkpoint into one portable model file that a laptop CPU and a phone app can run, gives the same detections as the training framework, and comes with a written contract for turning a photo into counts.

**Why this priority**: The model only becomes useful for teaching once something other than the training notebook can run it. It needs a trained checkpoint (Story 2); the choice of which one comes from Story 3.

**Independent Test**: Export a small untrained model, compare its outputs with the training framework's on inputs not used for the export, and confirm the comparison reports how many detections it checked; run the reference implementation of the contract on the boundary cases and confirm the golden fixtures for the app are up to date.

**Acceptance Scenarios**:

1. **Given** a checkpoint, **When** it is exported, **Then** the file has one input named for the image and two outputs (class scores and boxes) at a fixed size, and a record of its size and checksum and of the checkpoint it came from is written beside it.
2. **Given** an exported model and its checkpoint, **When** they are compared on 10 validation photos at the counting threshold, **Then** each photo keeps the same detections with the same classes, box overlap at least 0.99 and score difference at most 0.001, detections are paired by class and overlap rather than by list order, and the number compared is reported.
3. **Given** a photo with an orientation tag, in greyscale or with transparency, **When** it is prepared for the model, **Then** it is turned upright first, converted to colour, resized to the model's input size without keeping the aspect ratio and scaled to 0–1 without further normalisation.
4. **Given** a detection that scores exactly at the threshold, **When** the photo is counted, **Then** it is kept (the comparison is inclusive).
5. **Given** a change to the contract, **When** the golden fixtures are checked, **Then** the check fails until the fixtures are rebuilt from the reference.

---

### User Story 5 - Publish the weights for teaching, and only for teaching (Priority: P5)

An instructor or learner downloads a published model, checks that it is the file the project describes, reads what it may and may not be used for, and loads it into the demo app.

**Why this priority**: Publishing turns the work into something others can use, but it is also outward and hard to undo, so it comes last and only for a model that passed Stories 3 and 4.

**Independent Test**: Download one published model, compare its size and checksum with its model description in the repository, and confirm that the app's bundled list of published models holds the same descriptions.

**Acceptance Scenarios**:

1. **Given** a model that met the gates, **When** it is published, **Then** the published page holds the model file, its model description and its model card, under a licence that credits the dataset.
2. **Given** a model description, **When** the app or a reader parses it, **Then** it gives the model's identifier, label, architecture, base model, licence, input size, counting threshold, review level, checksum, size, outputs, number of classes, validation figures and a "validated" flag set to false; unknown or missing fields are rejected.
3. **Given** a published model, **When** anyone reads its card, **Then** it says the model is a teaching demo, not validated in the field, not made for farmers and not a basis for any pest-management decision.
4. **Given** the model files, **When** the repository is cloned, **Then** it contains the model descriptions only: no model weights, no training checkpoints and no dataset images.

---

### Edge Cases

- The dataset archive cannot be downloaded or its checksum differs: the download stops, the partial file is removed and a verified copy on the user's own cloud drive is accepted instead.
- An image named in the split is missing from the archive or its checksum differs: extraction stops and names the image.
- A tray holds more insects than the model has detection slots: the split build refuses it.
- A model finds nothing at the counting threshold: count accuracy then equals the do-nothing baseline, which the report shows beside it so the failure is visible.
- The best threshold sits at the top of the search grid: it is recorded as possibly capped, and the grid is not widened after the results.
- A history file ends in a half-written line after a disconnect: the line is dropped with a warning; damage anywhere else stops the run.
- Two runtimes rank near-equal scores in a different order: parity pairs detections by class and overlap, so order alone does not fail it.
- Training scores never reach the threshold even though detection quality is high: the scores are calibrated on validation and the cause is investigated; the threshold is never tuned on the test split.
- A later model needs judging after the test split has had its looks: it needs a new held-out set.

## Requirements *(mandatory)*

### Functional Requirements

**Data and split**

- **FR-001**: The pipeline MUST group each image with its augmented variants into a family and keep every family in exactly one split.
- **FR-002**: The pipeline MUST merge families whose representative photos are near-identical into one group before splitting, with a closeness limit chosen on the data and recorded.
- **FR-003**: The pipeline MUST split groups 70/15/15 into training, validation and test, balanced by species mix (rice black bug only, white stemborer only, both), with a fixed seed.
- **FR-004**: Training MUST keep every variant of its families; validation and test MUST keep exactly one image per family, chosen by a fixed rule that is recorded for each image.
- **FR-005**: The pipeline MUST validate every label and exclude a whole family with any invalid label, recording the reason; polygon outlines MUST become boxes.
- **FR-006**: The split MUST be stored as a manifest plus one label file per split, and MUST NOT include any image; the training environment MUST check each image it uses against the manifest's checksum.

**Training**

- **FR-007**: Training notebooks MUST be generated from the repository's own source and data files, never edited by hand, and a check MUST fail when a committed notebook differs from a fresh build.
- **FR-008**: Each notebook MUST pin the base model's revision and the training library's version, record its environment, and stop early when no GPU is attached.
- **FR-009**: Training MUST resume after a disconnect from the last epoch, MUST refuse to resume a different experiment, and MUST skip and count updates whose loss or gradient is not finite.
- **FR-010**: The best checkpoint MUST be chosen on validation species-level detection quality only; the test split MUST NOT be read during training.

**Evaluation and threshold**

- **FR-011**: Evaluation MUST report species-level and per-sex-class detection quality, count accuracy with the do-nothing baseline beside it, and per-species count error, bias, exact-count rate, presence recall and error by density (1–9, 10–29, 30 or more insects).
- **FR-012**: The counting threshold and any score calibration MUST be chosen on the validation split only, with counts reported out-of-fold over family-grouped folds.
- **FR-013**: Rules for choosing between models and for using the test split MUST be written down before the results they govern, and every result MUST be recorded with its run, split, date and source file.
- **FR-014**: A test result MUST be bound to the model, split, labels, threshold and evaluator version that produced it, and MUST be refused when any of them changes.

**Export and contract**

- **FR-015**: Export MUST produce a single portable model file with one image input and two outputs (raw class scores for 300 detection slots and their boxes) at a fixed input size, plus a record of its size and checksum.
- **FR-016**: Export MUST be checked against the training framework on 10 validation photos at the counting threshold, with the tolerances in SC-005, and the check MUST report how many detections it compared.
- **FR-017**: The steps that turn a photo into counts MUST be written down as one contract with one reference implementation, and golden fixtures generated from that reference MUST let other clients prove they follow it.

**Publishing and wording**

- **FR-018**: Each published model MUST have a strict model description in the repository (identifier, label, architecture, base model, licence, input size, threshold, review level, checksum, size, outputs, number of classes, validation figures, validated flag; an optional note) and a model card.
- **FR-019**: Model weights, checkpoints and dataset images MUST NOT be committed; weights are published separately and fetched by address with a pinned checksum.
- **FR-020**: Every model card and published page MUST describe the model as a teaching demo, not validated in the field and not for farmers, MUST credit the dataset as "its authors (Deleña et al.)" with its licence, and MUST NOT suggest a treatment, spray or other pest-management action.

### Key Entities

- **Family**: an original photo and its augmented variants; the unit that is never split.
- **Duplicate group**: one or more families whose representative photos are near-identical; the unit that is split.
- **Split manifest**: the record of every image used (family, group, split, rule used to pick it, source path, checksum, size, dimensions, boxes) and the seed.
- **Exclusion**: a family left out, with the reason.
- **Training run**: a notebook, its settings, its experiment fingerprint, its per-epoch history and its latest and best checkpoints.
- **Evaluation result**: the metrics of one model on one split at one threshold, with the identity of everything it depends on.
- **Pre-registered rule**: a written condition, fixed before the results, that decides a model choice or a use of the test split.
- **Exported model**: the portable model file with its size, checksum and source checkpoint.
- **Model description**: the strict, machine-readable summary of an exported model that the app reads.
- **Model card**: the human-readable account of a model's intended use, limits, figures and licences.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 0 families, 0 near-duplicate groups and 0 identical files appear in more than one split, and validation and test hold exactly one image per family.
- **SC-002**: The chosen model's species-level detection quality (mean average precision at 50% box overlap, rice black bug and white stemborer with sexes merged) on the held-out test photos is at least 0.80.
- **SC-003**: On the held-out test photos, at least 80% of photos have both species counted within ±10% of the true count (within ±1 when the true count is below 10), reported beside the do-nothing baseline.
- **SC-004**: The sexes are shown to users only if each of the four sex classes reaches at least 0.70 detection quality on the held-out test photos; otherwise counts are reported by species only.
- **SC-005**: The exported model file is at most 200 MB, and on 10 validation photos at its counting threshold it keeps the same detections and classes as the training framework, with box overlap of at least 0.99 and score differences of at most 0.001.
- **SC-006**: The exported model counts one photo in at most 5 seconds (median of 10 runs) on the reference laptop's CPU.
- **SC-007**: Every committed training notebook is byte-identical to a fresh build from the repository, and every committed golden fixture to a fresh build from the reference implementation.
- **SC-008**: Every number quoted in the README, the model cards and the decks can be found in the evaluation record with its run, split and date.
- **SC-009**: The test split is used only as the rules allowed: the evaluation record lists each look, its date and its rule, and any later evaluation on it is labelled as post-hoc and not used for a choice.

## Assumptions

- Users of this feature are maintainers, instructors and workshop participants; the model is a teaching demo, not a field tool, and nobody is asked to act on its counts.
- The dataset is the open light-trap dataset by its authors (Deleña et al.), under its own licence, downloaded from its public archive; the repository never redistributes its images.
- The photos in the dataset were stretched to 640 × 640 before release and contain no pest-free trays; results hold for photos like these, not for phone photos taken in the field.
- Training uses a free cloud GPU notebook with a 16 GB GPU; everything else runs on a laptop CPU.
- "The reference laptop" is the one laptop used for every CPU latency measurement in the evaluation record.
- The phone app that consumes the model is feature [002-mobile-app](../002-mobile-app/spec.md); the desktop app that will consume it is feature [003-desktop-app](../003-desktop-app/spec.md). Both read the same model descriptions and follow the same contract.
- Field validation, a phone latency target, a wording review and a data-protection review are release gates held outside this feature; until they are met, every model stays a demo.
- No clarification markers were needed: the README's "Status and release gates" section and the evaluation record already fix every gate and number used here.
