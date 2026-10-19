# Feature Specification: Trap Pest Counter (phone app)

**Feature Branch**: `002-mobile-app`

**Created**: 2026-10-19

**Status**: Implemented (Spec Kit record written 2026-10-19). The app was first designed with a brainstorming workflow before Spec Kit was added; this is the Spec Kit record of it.

**Input**: User description: "Build an Android demo app that counts rice black bug and white stemborer on a light-trap photo, with the trained model running on the phone. It flags photos whose count should be checked, keeps past counts, and shares a summary. The user can download, import, switch, delete and compare models. English and Filipino. It is a teaching demo for a workshop, not a tool for farmers."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Count the insects in a trap photo (Priority: P1)

A workshop participant or instructor installs the app, downloads the default model, takes or chooses a photo of a light trap, and sees how many rice black bug and white stemborer the model counted, with a reminder that the counts are experimental.

**Why this priority**: This is what the app is for; it shows a trained model running on a phone. Every other story builds on a working count.

**Independent Test**: On a fresh install, download the default model, choose a light-trap photo, and check that the result shows a count for each species, the model and its threshold, and the experimental notice.

**Acceptance Scenarios**:

1. **Given** a fresh install with no model, **When** the user opens the app, **Then** it says that no model is installed, the photo buttons are disabled, and it offers to download the model with its size in MB.
2. **Given** the user starts the download, **When** the file arrives and its size and checksum match, **Then** the model is installed and the app starts counting with it; **When** they do not match or the download fails, **Then** nothing is installed, the app stays without a model and says the download failed.
3. **Given** a model is installed, **When** the user takes a photo or chooses one from the phone, **Then** the app shows the count for each species, the model's name and counting threshold, and the experimental-estimate notice.
4. **Given** a photo with a low-confidence detection or more than 30 insects, **When** it is counted, **Then** the result asks the user to check the count against the photo and gives the reason.
5. **Given** a photo taken with the phone held sideways (rotated by its orientation tag), **When** it is counted, **Then** the model sees the photo upright, as the reference implementation does.

---

### User Story 2 - Keep, revisit and share past counts (Priority: P2)

The user comes back later, sees what was counted before, reopens a result and shares a short summary through the phone's share sheet.

**Why this priority**: It turns single counts into a record a learner can compare and talk about.

**Independent Test**: Count two photos, restart the app, and confirm both are listed newest first and each reopens with the same numbers and flags; share one and check the text.

**Acceptance Scenarios**:

1. **Given** at least one count, **When** the app starts, **Then** the home screen lists past counts newest first with the date and time, the count per species and a flag marker where a review was suggested.
2. **Given** a past count, **When** the user opens it, **Then** the same result screen appears with the same counts, flags, model and threshold.
3. **Given** a result, **When** the user taps "Share the counts", **Then** the phone's share sheet opens with a plain-text summary (date, both counts, model, threshold and "Counts are estimates; please review") and the app's copy of the photo.
4. **Given** the photo was later deleted from the phone's gallery, **When** the user reopens or shares the count, **Then** it still works, because the app keeps its own copy.

---

### User Story 3 - Choose and manage models (Priority: P3)

An instructor wants to show that different models count differently: they download the other published models, import one from files on the phone, switch between them and delete one they no longer need.

**Why this priority**: It supports the three-model case study, but the app is useful without it.

**Independent Test**: Download a second published model, switch to it, count a photo and see the demo-model banner; switch back and the banner is gone; delete the second model.

**Acceptance Scenarios**:

1. **Given** Settings, **When** the user opens the model list, **Then** every installed model is listed with its architecture, input size, counting threshold and validation count accuracy beside the score of counting nothing (0.474), with tags for "Default", "In use" and "Not validated".
2. **Given** the list of published models, **When** a model with the same file is already installed, **Then** it shows "Installed" (and "In use" when active) instead of a Download button; **When** the user taps Download, **Then** progress is shown with a cancel button, and a finished download is listed but not made active.
3. **Given** the user imports a model by choosing its description file and then its model file, **When** the size, checksum, input and output names and shapes, and a self-test on a synthetic image all pass, **Then** the model is added but not made active; **When** any check fails, **Then** nothing is added, copies are removed, a message says which check failed, and the current model stays in use.
4. **Given** the user taps an installed model, **When** it loads, **Then** it becomes the model in use; **When** it fails to load, **Then** the previous model stays in use and the app says so.
5. **Given** a model other than the default is in use, **When** the user counts a photo, **Then** a "Demo model, not validated" banner appears on the home screen, on the result, in past counts and at the start of a shared summary.
6. **Given** an imported or downloaded model that is not the default, **When** the user deletes it and confirms, **Then** it is removed; if it was in use, the app falls back to the default model. The default model cannot be deleted.

---

### User Story 4 - Compare models on one photo (Priority: P4)

The instructor takes or chooses one photo and sees the counts, review flags and time taken by every installed model, side by side.

**Why this priority**: A teaching aid on top of Story 3.

**Independent Test**: With two models installed, compare one photo and confirm there is one row per model with counts, flags and time, and that nothing is added to past counts.

**Acceptance Scenarios**:

1. **Given** at least one installed model, **When** the user compares a photo, **Then** each model's counts, review flags and time appear as it finishes, with only one model loaded at a time.
2. **Given** a model that fails on the photo, **When** the comparison runs, **Then** that row says the model could not count the photo and the other models still run.
3. **Given** a comparison, **When** it finishes or the screen is closed, **Then** the model in use is unchanged, nothing is added to past counts, and the app's copy of the compared photo is removed.

---

### User Story 5 - Use the app in Filipino (Priority: P5)

A participant whose phone is set to Filipino sees the app in Filipino.

**Why this priority**: The workshop audience reads both languages; the Filipino text is still a draft, so it is lowest priority.

**Independent Test**: Set the phone's language to Filipino and check that the home, result, settings and compare screens show Filipino text.

**Acceptance Scenarios**:

1. **Given** the phone's language is Filipino, **When** the app starts, **Then** every screen shows Filipino; for any other language it shows English.
2. **Given** either language, **When** any text is shown, **Then** it has a counterpart in the other language with the same placeholders.

---

### Edge Cases

- A photo smaller than 32 pixels on a side: refused with "This photo is too small", and no count is recorded.
- A file that is not a readable image: refused with "This file could not be opened as a photo", and no count is recorded.
- The user cancels the camera, the photo chooser or either file chooser during an import: nothing happens.
- The connection drops, the server returns an error, or more bytes arrive than the model's description gives: the download stops, the partial file is removed, and the current model stays in use.
- A model whose description has a missing or unknown field, an input size outside 320–1280, or a threshold at or below the detector's floor: rejected at import or in the bundled catalogue.
- A model with the same identifier as an installed one: refused; the installed one is kept.
- The model chosen in Settings has been removed: the app starts with the default model instead.
- The history file is corrupt: it is set aside and a fresh history starts, so the app still opens.
- The same model file installed by two routes (the home-screen download and the Settings download): listed once.
- A photo with more than 30 insects: counted and flagged as crowded, because crowded trays have the largest errors.

## Requirements *(mandatory)*

### Functional Requirements

**Counting**

- **FR-001**: The app MUST count rice black bug and white stemborer on a photo taken with the camera or chosen from the phone, using a model that runs on the phone, with no network access while counting.
- **FR-002**: Counting MUST follow the project's inference contract (`docs/inference-contract.md`): orientation tag first, colour, resize, scaling, scoring and an inclusive threshold, as the reference implementation does.
- **FR-003**: The image preparation MUST be identical to the reference implementation's on the project's reference images; any step that cannot be identical MUST have its difference recorded.
- **FR-004**: The result MUST show the count per species, the model's label and threshold, and the experimental-estimate notice. Only species are reported, not sexes.
- **FR-005**: The result MUST ask for a review, with the reason, when any counted detection scores below the model's review level or more than 30 insects are counted.
- **FR-006**: The app MUST use each model's own counting threshold and review level from its description and MUST NOT offer a way to change them.
- **FR-007**: With no model installed the app MUST say so, disable the photo buttons, still open past counts, and offer the pinned model's download with its size.

**History and sharing**

- **FR-008**: Each completed count MUST be saved on the phone with its date and time, counts, review reasons, threshold, model and whether the model was the default, together with the app's own copy of the photo, and listed newest first.
- **FR-009**: The user MUST be able to reopen any past count and share a text summary and the photo through the phone's share sheet, only when they tap Share.

**Models**

- **FR-010**: The app MUST offer the three published models from a catalogue bundled with the app and download one only when the user asks, showing progress and allowing cancel.
- **FR-011**: A model MUST be used only after its size and checksum match its description, its input and output names and shapes match the contract at its input size, and a self-test on a synthetic image gives outputs of the right length with finite values. On any failure nothing is installed and the model in use is kept.
- **FR-012**: The user MUST be able to import a model from a description file and a model file chosen on the phone (never from a typed address), with the same checks.
- **FR-013**: Model descriptions MUST be strict: a missing, unknown or out-of-range field rejects the model.
- **FR-014**: The user MUST be able to switch the model in use, and delete any installed model except the default after confirming; deleting the model in use falls back to the default.
- **FR-015**: The default model MUST be recognised by its file's checksum, not by its name, and every other model MUST show a "Demo model, not validated" banner on the home screen, results, past counts and shared summaries. Every model, the default included, carries a "Not validated" tag.
- **FR-016**: The user MUST be able to compare one photo across all installed models, one loaded at a time, without saving to history or changing the model in use.
- **FR-017**: The app MUST NOT include a model in the installed package; counts come only from a real model the user downloaded, imported or placed.

**Wording, language and privacy**

- **FR-018**: The app MUST show a notice that matches its state (no model, demo model, published model) and an About screen with the intended use, privacy and licences.
- **FR-019**: No text in the app MAY suggest a treatment, spray or other pest-management action, address farmers or a technician as the audience, or name an organisation.
- **FR-020**: The app MUST offer English and Filipino, follow the phone's language, and have every text in both.
- **FR-021**: Photos, history and models MUST stay in the app's own storage. The only network access allowed is a model download the user starts, to an address in the bundled pin or catalogue. No analytics.

### Key Entities

- **Model**: a published, imported or placed detector, with its description (identifier, label, architecture, base model, licence, input size, counting threshold, review level, checksum, size, validation figures, validated flag, optional notes) and its file. One model is the default; at most one is chosen as in use.
- **Model pin**: the one model the home screen offers to download on a fresh install (address, checksum, size, threshold, label, kind).
- **Model catalogue**: the published models offered in Settings, each a download address and an unchanged model description; bundled with the app.
- **Count record**: one completed count (identifier, date and time, the app's copy of the photo, counts per species, review reasons, threshold, model, not-validated flag).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: On the project's reference images, the app's prepared model input is identical to the reference implementation's for all 8 orientation tags, all 8 reference image shapes at the default input size and all 7 at the smaller one (576), and its kept detections equal the reference's on all 3 reference output cases, including a score of exactly 0.5.
- **SC-002**: Each of the 7 failure kinds (network error, cancel, wrong size, too many bytes, wrong checksum, wrong inputs or outputs, failed self-test) leaves the same model in use and no leftover files.
- **SC-003**: The app makes no network request other than a model download the user started, to a bundled address.
- **SC-004**: Both languages have the same set of texts with the same placeholders (0 missing), and 0 texts contain a treatment, spray, audience or organisation word from the project's list.
- **SC-005**: On a reference low-end phone, a count appears within 5 seconds of choosing a photo with the default model (proposed target, matching the laptop gate of 5 seconds).
- **SC-006**: The Filipino text is reviewed by a native speaker before the app is used outside the workshop.

## Assumptions

- Users are workshop participants and instructors learning how a model is put behind a phone app. The app is not made for farmers, is not official, and has not been validated in the field (README notice; release gates 2–6 are open).
- Android only; iOS is out of scope.
- The model, its thresholds and its review levels come from the model pipeline ([001-model-training](../001-model-training/spec.md)); the app never chooses its own.
- The default model is r50-v5. All three published models carry "validated": false.
- The weights are too large for the repository and are published on a public model hub; the repository holds only their descriptions (`models/*.manifest.json`).
- No trap photos are stored in the repository (dataset licence and size). Reference images for SC-001 are deterministic patterns rebuilt from a formula.
- The dataset is credited to its authors (Deleña et al.).
- The phone's language decides the app's language; an in-app language setting is not needed for the workshop.
- History is small (tens to hundreds of counts per user), so one file is enough.
- A developer may place a demo model by hand over a USB cable; this is a developer route, not a user feature.
- The desktop version of this app is a separate feature ([003-desktop-app](../003-desktop-app/spec.md)).
