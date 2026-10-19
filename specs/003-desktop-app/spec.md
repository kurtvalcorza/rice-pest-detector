# Feature Specification: Desktop Trap Pest Counter

**Feature Branch**: `003-desktop-app`

**Created**: 2026-10-19

**Status**: Draft

**Input**: User description: "Build a desktop version of the Trap Pest Counter demo app for Windows, macOS and Linux, with the same features as the phone app: pick or drop a light-trap photo, count rice black bug and white stemborer with a model running on the computer, show review flags, keep past counts, and download, import, switch, delete and compare models. English and Filipino."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Count the insects in a trap photo (Priority: P1)

A workshop participant or instructor, on a laptop with no phone at hand, opens the app, gets the default model, picks a light-trap photo from their computer (or drops it onto the window) and sees how many rice black bug and white stemborer the model counted, with a reminder that the counts are experimental.

**Why this priority**: This is the whole point of the app; every other story builds on a working count. It also lets the workshop show the model running on a computer without an emulator or a phone.

**Independent Test**: On a fresh install, download the default model, open one of the listed validation photos and compare the counts with the reference counts for that photo.

**Acceptance Scenarios**:

1. **Given** a fresh install with no model, **When** the user opens the app, **Then** it says that no model is installed, the photo controls are disabled, and it offers to download the default model with its size.
2. **Given** the user starts the download, **When** the file arrives and its size and checksum match, **Then** the model is installed and becomes the active model; **When** they do not match, or the download fails or is cancelled, **Then** nothing is installed, the partial file is removed and the app says why.
3. **Given** the default model is installed, **When** the user picks or drops a JPEG or PNG photo, **Then** the app shows the count for each species, the photo, the model name and its counting threshold, and the experimental-estimate notice.
4. **Given** a photo with low-confidence detections or more than 30 insects, **When** it is counted, **Then** the result says the count should be checked against the photo and gives the reason.
5. **Given** a photo taken in portrait on a phone (rotated by its orientation tag), **When** it is counted, **Then** the counts are the same as for the same photo stored upright.

---

### User Story 2 - Keep and revisit past counts (Priority: P2)

The user comes back later and wants to see what was counted before, reopen a result and copy a summary to paste into notes or a message.

**Why this priority**: It turns single counts into a record a learner can compare and talk about; it is the second thing the phone app does.

**Independent Test**: Count two photos, restart the app, and confirm both counts are listed newest first and each reopens with the same numbers and flags.

**Acceptance Scenarios**:

1. **Given** at least one count, **When** the app starts, **Then** the home screen lists past counts newest first with date, time, the count per species and a flag marker where a review was suggested.
2. **Given** a past count, **When** the user opens it, **Then** the same result screen appears with the photo, and the user can show the app's copy of the photo in its folder.
3. **Given** a result, **When** the user copies the counts, **Then** a plain-text summary with the date, the counts and the experimental notice is placed on the clipboard (and the demo-model notice if the model is not the default).
4. **Given** the original photo has since been moved or deleted, **When** the user opens that past count, **Then** the counts and the photo still show, because the app keeps its own copy.

---

### User Story 3 - Choose and manage models (Priority: P3)

An instructor wants to show that different models count differently: they download the other published models, import one from a file, switch between them, and delete one they no longer need.

**Why this priority**: It supports the training case study (three models compared), but the app is useful without it.

**Independent Test**: Download a second published model, switch to it, count a photo and see the demo-model banner; switch back and the banner is gone; delete the second model.

**Acceptance Scenarios**:

1. **Given** the settings screen, **When** the user opens the model list, **Then** every installed model is listed with its label, architecture, input size, threshold and validation count accuracy, the active one marked, alongside the score of doing nothing (counting zero) on the same photos.
2. **Given** the published-models list, **When** a model is already installed, **Then** it is marked "Installed" (and "In use" if active) instead of offering a download.
3. **Given** the user imports a model description file and then its model file, **When** the size, checksum, input and output names and shapes, and a self-test on a synthetic image all pass, **Then** the model is added; **When** any check fails, **Then** nothing is added, copies are removed, the reason is shown and the current model stays active.
4. **Given** a non-default model is active, **When** the user counts a photo, **Then** a "demo model, not validated" banner appears on the home screen, on the result and in any copied summary.
5. **Given** an installed model that is not the default, **When** the user deletes it and confirms, **Then** it is removed, and if it was active the default model becomes active; the default model cannot be deleted.

---

### User Story 4 - Compare models on one photo (Priority: P4)

The instructor picks one photo and sees the counts, flags and time taken by every installed model side by side.

**Why this priority**: A teaching aid on top of Story 3; nice to have.

**Independent Test**: With two models installed, compare one photo and confirm one row per model with counts, flags and time, and that nothing is added to past counts.

**Acceptance Scenarios**:

1. **Given** two or more models installed, **When** the user compares a photo, **Then** each model's counts, review flags and time appear as each finishes, with only one model loaded in memory at a time.
2. **Given** a comparison, **When** it finishes or is cancelled, **Then** the active model is unchanged and no entry is added to past counts.

---

### User Story 5 - Use the app in Filipino (Priority: P5)

A participant whose computer is set to Filipino sees the app in Filipino; anyone can change the language in settings.

**Why this priority**: Matches the phone app; the Filipino text is still a draft, so it is lowest priority.

**Independent Test**: Set the language to Filipino in settings and check that every screen shows Filipino text with no English left over.

**Acceptance Scenarios**:

1. **Given** the computer's language is Filipino or Tagalog, **When** the app starts for the first time, **Then** it shows Filipino; otherwise English.
2. **Given** settings, **When** the user picks a language, **Then** the app switches immediately and remembers the choice.

---

### Edge Cases

- A photo smaller than 32 pixels on a side, not an image, corrupt, or in an unsupported format: the app refuses it with a clear message and records nothing.
- A very large photo (for example 12,000 × 9,000 pixels): it is counted, or refused with a clear message if it cannot be loaded; the app does not freeze or crash.
- The user drops several files at once: the app counts the first and says the others were ignored.
- The disk is full or the data folder cannot be written: the count is shown but the app says it could not be saved; a model download stops cleanly.
- The computer goes offline during a download: the download fails cleanly as in Story 1, scenario 2.
- Two copies of the app are opened: the second either brings the first to the front or works without corrupting past counts or models.
- The active model's file is removed outside the app: the app falls back to "no model" or to the default model, and says so, at the next start.
- A model whose threshold or review setting is missing from its description is rejected at import (descriptions are strict).

## Requirements *(mandatory)*

### Functional Requirements

**Counting**

- **FR-001**: The app MUST count rice black bug and white stemborer on a user-chosen photo using a model that runs on the user's computer, with no network access during counting.
- **FR-002**: Counting MUST follow the project's inference contract and give the same kept detections as the reference implementation for the same image and model, within the contract's stated tolerance.
- **FR-003**: Photos MUST be accepted by choosing a file and by dropping a file onto the window; JPEG and PNG MUST be supported.
- **FR-004**: The app MUST apply a photo's orientation tag before counting.
- **FR-005**: The result MUST show the count per species, the photo, the model's label and threshold, and the experimental-estimate notice.
- **FR-006**: The result MUST flag a photo for review, with the reason, when any kept detection scores below the model's review level or the photo has more than 30 insects.
- **FR-007**: The app MUST use each model's own counting threshold and review level from its description and MUST NOT offer a way to change them.

**History**

- **FR-008**: Each completed count MUST be saved on the computer with its date and time, the counts, the flags and the model used, together with a copy of the photo in the app's data folder, and listed newest first.
- **FR-009**: The saved history MUST use the same record format as the phone app.
- **FR-010**: The user MUST be able to reopen any past count, copy a text summary of a result, and show a result's photo in its folder.

**Models**

- **FR-011**: The app MUST offer the three published models from the project's model catalogue and download one only when the user asks, showing progress and allowing cancel.
- **FR-012**: A model MUST be installed only after its size and checksum match its description, its input and output names and shapes match the contract, and a self-test on a synthetic image gives finite outputs of the right shape. On any failure nothing is installed and the active model is kept.
- **FR-013**: The user MUST be able to import a model from a description file and a model file on the computer, with the same checks.
- **FR-014**: The user MUST be able to switch the active model and to delete any installed model except the default, after confirming; deleting the active model makes the default active (as on the phone).
- **FR-015**: The app MUST show a "demo model, not validated" banner whenever the active model is not the default, on the home screen, on results, in comparisons and in copied summaries.
- **FR-016**: The user MUST be able to compare one photo across all installed models, one model loaded at a time, without saving to history or changing the active model.

**Wording, language and privacy**

- **FR-017**: The app MUST show a not-validated notice whenever a model is in use, and an About screen with the intended use, privacy and licences.
- **FR-018**: No text in the app MAY suggest a treatment, spray or other pest-management action.
- **FR-019**: The app MUST offer English and Filipino, follow the computer's language on first start, and let the user change language in settings. Shared text MUST come from the phone app's text, with desktop wording only where the phone wording would be wrong (for example, "phone").
- **FR-020**: Photos, history and models MUST stay on the computer in the app's own data folder. The only network access allowed is a model download the user starts, to a catalogue address. No analytics or telemetry.
- **FR-021**: The app MUST run on Windows 10 and 11, macOS 14 or later, and a current desktop Linux, and be installable by someone without developer tools.

### Key Entities

- **Model**: a published or imported detector, with its description (identifier, label, architecture, input size, counting threshold, review level, checksum, size, validation figures, validated flag) and its file; one model is active and one is the default.
- **Model catalogue**: the list of published models and where to download them; shared with the phone app.
- **Count record**: one completed count (date and time, counts per species, flags and reasons, model used, the app's copy of the photo).
- **Settings**: the active model and the chosen language.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: On a fixed list of 20 validation photos from the project's dataset, the app's counts and review flags equal the reference implementation's for each of the three published models (0 differences out of 60 photo-model pairs).
- **SC-002**: On a reference laptop, a count appears within 5 seconds of choosing a photo with the default model, matching the project's CPU latency gate.
- **SC-003**: A first-time user goes from opening the installed app to a first count, including the model download on a normal connection, in under 5 minutes without help.
- **SC-004**: Every failed download, import or check leaves the app with the same active model and no leftover partial files (verified for each failure listed in the edge cases).
- **SC-005**: Over a session of counting, the app makes no network request other than a model download the user started.
- **SC-006**: Every screen is fully translated in both languages (0 strings left untranslated) and no string matches the treatment and spray words that the phone app's tests already reject.

## Assumptions

- Users are workshop participants and instructors on a personal laptop, not farmers; the app is a teaching demo under the same notices as the phone app.
- "The phone app" means feature [002-mobile-app](../002-mobile-app/spec.md), as built.
- Full parity with the phone app is wanted, except where a desktop has no equivalent: no camera (choose or drop a file instead), and copy to the clipboard instead of a phone share sheet. One deliberate addition: the result screen shows the photo, which the phone's result screen does not (a laptop screen has room for it).
- The phone's developer side-loading over a USB cable is not needed; import from a file covers that case.
- The model catalogue, model descriptions, text strings and contract fixtures already in the repository are the sources of truth and are reused, not copied.
- No trap photos are stored in the repository (dataset licence and size). The 20 photos for SC-001 are named in a list and fetched with the project's data pipeline; their reference counts are produced by the reference implementation, not hand-labelled.
- The independent test in Story 1 uses any photo from that list.
- Distribution as unsigned installers is acceptable for a teaching demo; signing and auto-update are out of scope for this version.
- A reference laptop is the one used for the project's CPU latency gate.
