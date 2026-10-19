---
description: "Task list for the Trap Pest Counter phone app"
---

# Tasks: Trap Pest Counter (phone app)

**Input**: Design documents from `/specs/002-mobile-app/`

**Prerequisites**: [plan.md](plan.md), [spec.md](spec.md), [research.md](research.md), [data-model.md](data-model.md), [contracts/](contracts/), [quickstart.md](quickstart.md)

**Status**: The app is built. Each done task `[x]` ends with the files that implement it (→). Open tasks `[ ]` are work that does not exist in the repository yet.

**Tests**: Required. Constitution Principle III (test-first) is non-negotiable: every test task below was written first and failed for the right reason before its implementation task.

**Organization**: Tasks are grouped by user story so each story can be built, tested and shown on its own.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependency on an unfinished task)
- **[Story]**: The user story the task belongs to (US1–US5)
- Paths are from the repository root; app code is under `app/`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: A Flutter project for Android, its dependencies, localisation, CI, and golden fixtures from the Python reference.

- [x] T001 Create the Flutter project for Android in `app/` (package `rice_pest_app`) with `flutter_lints` → app/pubspec.yaml, app/analysis_options.yaml, app/android/
- [x] T002 Add the dependencies: `flutter_onnxruntime` ^1.9.0, `image` ^4.12.0, `image_picker` ^1.2.4, `share_plus` ^13.3.1, `file_selector` ^1.1.0, `path_provider` ^2.1.6, `http` ^1.6.0, `crypto` ^3.0.7, `intl` ^0.20.3, `flutter_localizations`, `integration_test` → app/pubspec.yaml
- [x] T003 [P] Set up `gen-l10n` with English as the template and Filipino beside it → app/l10n.yaml, app/lib/l10n/app_en.arb, app/lib/l10n/app_fil.arb
- [x] T004 [P] Add a CI job that runs `flutter analyze` and `flutter test` at Flutter 3.47.7 → .github/workflows/tests.yml
- [x] T005 [P] Python tests for the fixture generator (stable output, `--check` fails on stale fixtures) → tests/test_export_app_fixtures.py
- [x] T006 Write the golden-fixture generator from `src/rice_pest_detector/infer.py` (orientations 1–8, resize of 8 shapes at 640, 3 post-processing cases, no photos), with `--check`, and run it in CI (T005 passes) → tools/export_app_fixtures.py, app/test/fixtures/contract_fixtures.json, .github/workflows/tests.yml
- [x] T007 [P] Write the resize-fixture generator for other input sizes (7 shapes at 576), with `--check` in CI → app/tool/export_resize_fixtures.py, app/test/fixtures/resize_fixtures.json, .github/workflows/tests.yml

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: The inference contract in Dart, the detector interface and the service interfaces every story uses.

**⚠️ CRITICAL**: No user story work could begin until this phase was complete.

- [x] T008 Test that the contract constants (input size 640, threshold 0.5, 300 queries, class names, species map, tensor names) match the Python package → app/test/contract_test.dart
- [x] T009 Define the contract constants, including `detectorFloor` 0.02 (T008 passes) → app/lib/inference/contract.dart
- [x] T010 Tests: EXIF orientations 1–8 match Pillow; resize byte-identical to Pillow at 640 and at 576; tensor is NCHW float32 ÷ 255; photos under 32 px a side are rejected; `preprocess` uses the model's input size → app/test/contract_test.dart
- [x] T011 Port Pillow 12.3's bilinear resampler (fixed point, 22 bits, horizontal pass first), `applyExifOrientation`, `toTensor` and `PhotoTooSmall` (T010 passes) → app/lib/inference/preprocess.dart
- [x] T012 Test that post-processing matches the reference on 3 cases, including a score of exactly 0.5 kept at 0.5 → app/test/contract_test.dart
- [x] T013 Implement `postprocess`: sigmoid in double precision, max over classes, `score >= threshold`, boxes on the upright size, sort by score with ties in query order (T012 passes) → app/lib/inference/postprocess.dart
- [x] T014 [P] Tests: `decodePhoto` returns the photo upright for tags 1–8 (matching Pillow), turns RGBA and grey into RGB, and raises `PhotoUnreadable` on bad bytes → app/test/decode_test.dart
- [x] T015 Implement `decodePhoto` with the `image` package (T014 passes) → app/lib/inference/decode.dart
- [x] T016 [P] Tests: `FakeDetector` replays recorded detections sorted by score and refuses an unknown photo → app/test/detector_test.dart
- [x] T017 Define `Detector`, `PhotoRef` and `FakeDetector` (T016 passes) → app/lib/inference/detector.dart
- [x] T018 Test that the detector floor is below the lowest demo threshold → app/test/onnx_detector_floor_test.dart
- [x] T019 Implement `OnnxDetector` on `flutter_onnxruntime` with a per-model input size, dropping scores below the floor (T018 passes) → app/lib/inference/onnx_detector.dart
- [x] T020 Define the service interfaces (`PhotoSource`, `Sharer`, `ModelMode`, `AppServices`, `formatTakenAt`) and the test fakes → app/lib/app/services.dart, app/test/ui_test.dart

**Checkpoint**: Foundation ready; user stories can begin.

---

## Phase 3: User Story 1 - Count the insects in a trap photo (Priority: P1) 🎯 MVP

**Goal**: Download the default model, take or choose a photo, and see the counts with the right notice and review flags.

**Independent Test**: Fresh install → download the default model → choose a light-trap photo → counts per species, model, threshold and the experimental notice are shown.

### Tests for User Story 1 ⚠️ written first, seen to fail

- [x] T021 [P] [US1] Counting tests: the threshold is inclusive; review flags for low confidence and crowding; each model brings its own threshold and review level; the default review level is 0.64 and crowding is more than 30 → app/test/counting_test.dart
- [x] T022 [P] [US1] Pin and store tests: the pin's shape, threshold, label and kind; download streams to `.part` and verifies size and SHA-256; a corrupted download or HTTP error installs nothing; an unset pin refuses to download; a local file verifies the same pin → app/test/model_store_test.dart
- [x] T023 [P] [US1] Start-up tests: an installed demo pin runs in demo mode at its threshold; a published pin without a threshold uses 0.50; a set pin that is not installed offers the download and does not count; an empty pin offers nothing; a `demo.json` side-load works → app/test/bootstrap_test.dart
- [x] T024 [P] [US1] Widget tests: home shows the notice and photo buttons; with no model the app says so and cannot count; a photo is counted, flagged, saved and shown; a too-small photo explains itself and saves nothing; demo mode shows its notice and threshold; the download is offered with its size, reloads the app on success and keeps the no-model state on failure → app/test/ui_test.dart

### Implementation for User Story 1

- [x] T025 [P] [US1] Implement `countPhoto` with species counts and the `lowConfidence` and `crowded` reasons (T021 passes) → app/lib/counting/counting.dart
- [x] T026 [P] [US1] Implement `ModelPin`, `fetchToFile` (streamed, paused per chunk, cancellable) and `ModelStore` (`.part`, size and SHA-256, rename) (T022 passes) → app/lib/model/model_store.dart
- [x] T027 [US1] Implement `chooseModel` and the `none`, `demo` and `published` modes (T023 passes) → app/lib/app/bootstrap.dart
- [x] T028 [P] [US1] Implement `ImagePickerSource`: camera and gallery with no resize or recompression, copied into `photos/` → app/lib/app/platform_services.dart
- [x] T029 [US1] Build the home screen: the notice for each mode, the download button, camera and gallery buttons disabled without a model, the counting progress, and the too-small and unreadable messages (T024 passes) → app/lib/ui/home_screen.dart
- [x] T030 [US1] Build the result screen: count per species, review reasons, the experimental notice, model and threshold → app/lib/ui/result_screen.dart
- [x] T031 [P] [US1] Add the US1 strings in English and Filipino → app/lib/l10n/app_en.arb, app/lib/l10n/app_fil.arb
- [x] T032 [US1] Pin r50-v5 for download (`"kind": "demo"`, threshold 0.48) and bundle no model: the only assets are the pin and the catalogue → app/assets/model_pin.json, app/pubspec.yaml
- [x] T033 [US1] Remove the bundled 9.9 KB constant-output test model, so a fresh install starts with no model (research R8) → app/pubspec.yaml, README.md
- [x] T034 [US1] Wire `main.dart` (documents folder, pin, stores, start-up choice) and `RicePestApp` with `reload` after a download → app/lib/main.dart, app/lib/app/app.dart
- [x] T035 [US1] On-device smoke test: with no model the real app starts, says so and cannot count → app/integration_test/app_smoke_test.dart, app/test_driver/integration_test.dart
- [ ] T036 [US1] Time a count with the default model on a reference low-end phone (median of 10) and record it against SC-005 and release gate 6 in `docs/evaluation-record.md`
- [ ] T037 [US1] Run the default model on validation photos on a phone and compare kept detections with the reference implementation, to measure the JPEG decoder difference (Principle II); record it in `docs/evaluation-record.md`

**Checkpoint**: User Story 1 works on its own: the MVP.

---

## Phase 4: User Story 2 - Keep, revisit and share past counts (Priority: P2)

**Goal**: Past counts listed newest first, reopened, and shared through the share sheet.

**Independent Test**: Count two photos, restart, both are listed newest first and reopen with the same numbers and flags; share one.

### Tests for User Story 2 ⚠️

- [x] T038 [P] [US2] History tests: entries round-trip and load newest first; delete removes the entry and its photo; a corrupt file is set aside; writes leave no temp file; entries record `notValidated`, and old entries read as false → app/test/history_test.dart
- [x] T039 [P] [US2] Widget tests: share sends a reviewable summary and the photo, with no treatment advice; past counts are listed newest first and open again → app/test/ui_test.dart

### Implementation for User Story 2

- [x] T040 [US2] Implement `HistoryEntry` and `HistoryStore`: one JSON file, `.tmp` and rename, `.corrupt` on a bad file (T038 passes) → app/lib/storage/history.dart
- [x] T041 [US2] List past counts on the home screen with date, counts and a flag icon, and reopen them on the result screen → app/lib/ui/home_screen.dart
- [x] T042 [P] [US2] Implement `SharePlusSharer` (text plus the photo if it still exists) → app/lib/app/platform_services.dart
- [x] T043 [US2] Add "Share the counts" and the summary text to the result screen (T039 passes) → app/lib/ui/result_screen.dart, app/lib/l10n/app_en.arb, app/lib/l10n/app_fil.arb
- [x] T044 [US2] Record the decision to keep history as JSON, not SQLite → docs/decisions.md

**Checkpoint**: User Stories 1 and 2 both work on their own.

---

## Phase 5: User Story 3 - Choose and manage models (Priority: P3)

**Goal**: Download, import, switch and delete models, each verified before use, with the not-validated banner for any non-default model.

**Independent Test**: Download a second published model, switch to it, count and see the banner; switch back; delete it.

### Tests for User Story 3 ⚠️

- [x] T045 [P] [US3] Manifest tests: a complete manifest parses; `notes` optional; each missing field, unknown field and wrong type rejected; `input_size` 320 to 1280; thresholds strictly between 0 and 1 with `review_below` not under `threshold`; `threshold` above the detector floor; fixed outputs, 4 classes, SHA-256, positive size, safe id; validation figures in range → app/test/model_manifest_test.dart
- [x] T046 [P] [US3] Catalogue tests: three published models with https URLs; each manifest equals its file in `models/`; the parser rejects anything unexpected → app/test/published_models_test.dart
- [x] T047 [P] [US3] Test that the pin matches the default model's catalogue entry → app/test/model_pin_test.dart
- [x] T048 [P] [US3] Registry tests: import copies into its own folder and does not change the active model; wrong size, wrong SHA-256, invalid manifest and failed session check leave nothing behind; a repeated id is refused; the active id persists; deleting clears it; the default (by SHA-256) cannot be deleted; hand-placed models are listed once verified; bad folders are skipped; default first, then by label → app/test/model_registry_test.dart
- [x] T049 [P] [US3] Session-check tests: a matching model passes at its own input size and is closed; a dynamic batch is accepted; wrong input size, names or shapes are shape mismatches; wrong lengths or non-finite outputs and a session that will not open fail the self-test → app/test/model_check_test.dart
- [x] T050 [P] [US3] Download tests: a published model installs and is listed but not made active; progress without a total; short, oversized and wrong-checksum files, failed self-tests, wrong shapes, HTTP errors, broken connections and cancels all roll back; an installed model is not downloaded again → app/test/model_download_test.dart
- [x] T051 [P] [US3] Start-up tests with the registry: the active model wins with its own input size, threshold and review level; a validated model runs in published mode; a non-default model is never picked on its own; a missing active model falls back to the default; legacy pins can be made active; models from all three routes are listed once → app/test/bootstrap_test.dart
- [x] T052 [P] [US3] Settings widget tests: the list with facts and tags; switching reloads and shows the banner; a failed load restores the previous model; the banner on the result, in history and in shared text, and none for the default; each import failure has its own message; cancelling a picker does nothing; deleting the active model asks first and falls back to the default → app/test/models_ui_test.dart
- [x] T053 [P] [US3] Download widget tests: each published model with its facts and size; "Installed" only on a SHA-256 match; progress and cancel; an indeterminate bar without a total; a finished download not made active; a message per failure; the real catalogue over a fake HTTP client → app/test/settings_download_test.dart

### Implementation for User Story 3

- [x] T054 [US3] Implement the strict `ModelManifest` parser and `doNothingCountAccuracy` 0.474 (T045 passes) → app/lib/model/model_manifest.dart
- [x] T055 [P] [US3] Write the manifests of the three published models → models/rice-pest-r50-v5.manifest.json, models/rice-pest-rfdetr-m.manifest.json, models/rice-pest-dfine-l.manifest.json
- [x] T056 [US3] Implement `parsePublishedModels` and bundle the catalogue (T046, T047 pass) → app/lib/model/published_models.dart, app/assets/model_catalog.json
- [x] T057 [US3] Implement `ModelRegistry`: staging folder, size and SHA-256, caller's check, verification stamp, `active.json`, default identified by SHA-256 (T048 passes) → app/lib/model/model_registry.dart
- [x] T058 [US3] Implement `checkModel` with a synthetic 64 × 48 pattern, and `OnnxProbe` (T049 passes) → app/lib/inference/model_check.dart, app/lib/inference/onnx_detector.dart
- [x] T059 [US3] Implement `LocalModelCatalog` (list, activate, delete, import, download to `.download-<id>.part`) and `FileSelectorModelFiles` (T050 passes) → app/lib/app/model_catalog.dart
- [x] T060 [US3] List registry, pin and side-loaded models together and honour the active choice at start-up (T051 passes) → app/lib/app/bootstrap.dart
- [x] T061 [US3] Add `ModelCatalog` and `ModelFilePicker` to the service interfaces, and `notValidated` to `AppServices` and `HistoryEntry` → app/lib/app/services.dart, app/lib/storage/history.dart
- [x] T062 [US3] Build the Settings screen: model list with tags, tap to use, delete with confirmation, import, and the download list with progress and cancel (T052, T053 pass) → app/lib/ui/settings_screen.dart
- [x] T063 [US3] Show the "Demo model, not validated" banner on the home screen and results, and prefix shared summaries with it → app/lib/ui/not_validated_banner.dart, app/lib/ui/home_screen.dart, app/lib/ui/result_screen.dart
- [x] T064 [P] [US3] Add the model strings in English and Filipino → app/lib/l10n/app_en.arb, app/lib/l10n/app_fil.arb
- [x] T065 [US3] Wire the registry, catalogue and file picker in `main.dart`, and reload after a switch or delete → app/lib/main.dart, app/lib/app/app.dart

**Checkpoint**: User Stories 1–3 work on their own.

---

## Phase 6: User Story 4 - Compare models on one photo (Priority: P4)

**Goal**: One photo, every installed model, one loaded at a time, nothing saved.

**Independent Test**: With two models installed, compare one photo: one row per model, nothing added to history.

- [x] T066 [P] [US4] Widget tests: compare counts one photo with every installed model, one at a time, labelled as demo models; a failing model is reported and the others still run; the app's copy of the compared photo is deleted when the screen closes → app/test/models_ui_test.dart
- [x] T067 [US4] Build the compare screen (reuse the active detector, open and close the others in turn, time each run) and its button in Settings (T066 passes) → app/lib/ui/compare_screen.dart, app/lib/ui/settings_screen.dart
- [x] T068 [P] [US4] Add the compare strings in English and Filipino → app/lib/l10n/app_en.arb, app/lib/l10n/app_fil.arb

**Checkpoint**: User Stories 1–4 work on their own.

---

## Phase 7: User Story 5 - Use the app in Filipino (Priority: P5)

**Goal**: Every text in Filipino when the phone is set to Filipino.

**Independent Test**: Set the phone to Filipino: home, result, settings and compare in Filipino.

- [x] T069 [P] [US5] Tests: Filipino and English have the same keys and the same placeholders → app/test/l10n_test.dart
- [x] T070 [P] [US5] Widget tests: the Filipino locale shows Filipino text on the home screen, the model strings and the download section → app/test/ui_test.dart, app/test/models_ui_test.dart, app/test/settings_download_test.dart
- [x] T071 [US5] Write the Filipino draft of all 76 strings, including the pest names *atangya* and *puting aksip* (T069, T070 pass) → app/lib/l10n/app_fil.arb, app/lib/l10n/app_localizations_fil.dart
- [x] T072 [US5] Support `en` and `fil` and follow the phone's language (`locale` left null) → app/lib/l10n/app_localizations.dart, app/lib/app/app.dart
- [ ] T073 [US5] Have a native speaker review the Filipino text, including the pest names, and record the result (SC-006, release gate 4)

**Checkpoint**: All user stories work on their own.

---

## Phase 8: Polish & Cross-Cutting Concerns

- [x] T074 [P] Wording guard tests: no string gives treatment or spray advice, addresses farmers or a technician, or names an organisation; the notices exist → app/test/l10n_test.dart
- [x] T075 [P] Build the About screen with the intended use, privacy notice, data and code licences, and the open-source licence page → app/lib/ui/about_screen.dart, app/lib/l10n/app_en.arb, app/lib/l10n/app_fil.arb
- [x] T076 [P] Credit the dataset to its authors (Deleña et al.) in the notice file and the About text → NOTICE, app/lib/l10n/app_en.arb
- [x] T077 [P] Build release APKs per CPU type in CI and attach them to `app-v*` releases → .github/workflows/build-apk.yml
- [x] T078 [P] Add scripts that start an emulator and run the app, with a fresh-data option → tools/run_emulator.ps1, tools/run_emulator.sh
- [x] T079 [P] Document the app: model modes, switching, parity, build and test, run, privacy and wording → README.md, docs/setup.md
- [x] T080 Confirm the only network use is the model download the user starts: HTTP appears only in `fetchToFile` and its two callers, both reached from a Download tap (SC-003) → app/lib/model/model_store.dart, app/lib/app/model_catalog.dart, app/android/app/src/main/AndroidManifest.xml
- [ ] T081 Review the English text so nothing reads as agronomic advice, and record the review (release gate 4; the Filipino review is T073)
- [ ] T082 Review the in-app privacy notice for data protection (release gate 5)
- [ ] T083 Route the home-screen pinned download through the registry's checks, so it also passes the session self-test before use (Principle VI deviation in [plan.md](plan.md))
- [ ] T084 Measure the size of the split-per-ABI release APK and record it in `README.md`

---

## Dependencies & Execution Order

### Phase dependencies

- **Setup (Phase 1)** → **Foundational (Phase 2)** → user stories.
- **User stories (Phases 3–7)**: US1 first (it is the MVP and brings counting, the pin download and the screens). US2 depends only on US1's result screen. US3 extends the start-up choice from US1 (T060 after T027). US4 needs US3's catalogue to open other models. US5 can run beside any story; each story adds its own strings in both languages.
- **Polish (Phase 8)** after the stories it covers. The open tasks (T036, T037, T073, T081–T084) do not block one another.

### Within each story

- Tests first, failing for the right reason (Principle III).
- Models and services before the screens that use them.
- Each milestone ended with the whole `flutter test` suite green and a commit.

### Parallel opportunities

- Phase 1: T003, T004, T005 and T007 together.
- Phase 2: T014 and T016 beside the contract work (T008–T013).
- US1: T021–T024 together; then T025, T026, T028 and T031 together.
- US3: T045–T053 together; T055 and T064 beside the implementation.

## Parallel example: User Story 3

```text
Task: "T045 Manifest tests in app/test/model_manifest_test.dart"
Task: "T048 Registry tests in app/test/model_registry_test.dart"
Task: "T049 Session-check tests in app/test/model_check_test.dart"
Task: "T050 Download tests in app/test/model_download_test.dart"
```

## Implementation Strategy

### MVP first (User Story 1 only)

1. Phase 1 and Phase 2: the contract must match the reference before anything else, because a resize that differs changes every count.
2. Phase 3 (US1): count a photo with a downloaded, verified model.
3. **Stop and validate**: on an emulator, a fresh install starts with no model, downloads it and counts.

### Incremental delivery

US1 → US2 (history, share) → US3 (models) → US4 (compare) → US5 (Filipino), each a milestone with green tests and a commit. Then the open release-gate tasks: phone latency (T036), on-device parity (T037), wording and Filipino reviews (T073, T081), data protection (T082).
