---
description: "Task list for the desktop Trap Pest Counter"
---

# Tasks: Desktop Trap Pest Counter

**Input**: Design documents from `/specs/003-desktop-app/`

**Prerequisites**: [plan.md](plan.md), [spec.md](spec.md), [research.md](research.md), [data-model.md](data-model.md), [contracts/](contracts/), [quickstart.md](quickstart.md)

**Tests**: Required. Constitution Principle III (test-first) is non-negotiable: every test task below is written first and must fail for the right reason before its implementation task starts.

**Organization**: Tasks are grouped by user story so each story can be built, tested and shown on its own.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependency on an unfinished task)
- **[Story]**: The user story the task belongs to (US1–US5)
- Paths are from the repository root; app code is under `app/`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Desktop targets exist and the existing suite still passes on them.

- [ ] T001 Generate desktop platform folders with `flutter create --platforms=windows,macos,linux .` in `app/`, keeping `lib/`, `test/` and `pubspec.yaml` unchanged
- [ ] T002 Set the macOS deployment target to 14.0 in `app/macos/Podfile` and `app/macos/Runner.xcodeproj` (research R7)
- [ ] T003 [P] Set the window title "Trap Pest Counter" and a minimum window size of 800 × 600 in `app/windows/runner/main.cpp`, `app/macos/Runner/MainFlutterWindow.swift` and `app/linux/runner/my_application.cc`
- [ ] T004 Run `flutter test` on the host and `flutter build windows|macos|linux` on each OS; record that the unchanged suite passes and the app starts on each desktop (no feature work yet)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Platform selection, data folder and the extended interfaces every story uses.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

- [ ] T005 Write failing tests for `dataDirectory()` (support folder on desktop, documents folder on phone, via an injected platform flag) in `app/test/data_dir_test.dart`
- [ ] T006 Add `desktop_drop` to `app/pubspec.yaml` and confirm it builds and receives a dropped file on Windows, macOS and Linux with a throwaway test window; if it fails on any OS, stop and revisit research R3
- [ ] T007 Implement `dataDirectory()` in `app/lib/app/data_dir.dart` and use it in `app/lib/main.dart` (T005 passes)
- [ ] T008 Add `fromFile(String path)` to `PhotoSource` and an optional `FolderRevealer` to `AppServices` in `app/lib/app/services.dart`; update the phone implementation and test fakes so the existing suite still passes
- [ ] T009 Choose phone or desktop services at start-up in `app/lib/main.dart` (`Platform.isWindows || isMacOS || isLinux`), with desktop services stubbed to throw `UnimplementedError`

**Checkpoint**: Foundation ready; user stories can begin.

---

## Phase 3: User Story 1 - Count the insects in a trap photo (Priority: P1) 🎯 MVP

**Goal**: On a computer, download the default model, choose or drop a photo, and see the counts with the right notices and flags.

**Independent Test**: Fresh install → download the default model → open one listed validation photo → counts equal the reference counts for that photo.

### Tests for User Story 1 ⚠️ write first, see them fail

- [ ] T010 [P] [US1] Unit tests for `DesktopPhotoSource.fromFile` (copies into `photos/`, rejects non-images, corrupt files and sides under 32 px with `PhotoRejected`) in `app/test/desktop_services_test.dart`
- [ ] T011 [P] [US1] Widget test: on desktop the home screen hides the camera button, shows "Choose a photo" and a drop area, disables both with no model, and counts the first of several dropped files with a notice, in `app/test/desktop_home_test.dart`
- [ ] T012 [P] [US1] Python tests for `tools/export_desktop_parity.py`: the selection rule picks 20 validation names reproducibly, never a test name, and `--check` fails on a changed list, in `tests/test_export_desktop_parity.py`
- [ ] T013 [US1] Integration test comparing counts and reasons exactly for every photo and published model in `app/test/fixtures/desktop_parity.json`, skipped when photos (`RPD_PARITY_PHOTOS`) or models are missing, in `app/integration_test/desktop_parity_test.dart`

### Implementation for User Story 1

- [ ] T014 [P] [US1] Implement `DesktopPhotoSource` (`gallery()` via `file_selector` with JPEG and PNG filters; `fromFile`) in `app/lib/app/desktop_services.dart` (T010 passes)
- [ ] T015 [US1] Add the drop area (`desktop_drop`) and hide the camera button on desktop in `app/lib/ui/home_screen.dart` (T011 passes)
- [ ] T016 [P] [US1] Add desktop-only strings (for example "Choose a photo or drop it here", "Only the first photo was used", wording that says "computer" instead of "phone") to `app/lib/l10n/app_en.arb` and `app/lib/l10n/app_fil.arb`; regenerate localisations; `app/test/l10n_test.dart` covers the new keys
- [ ] T017 [US1] Implement `tools/export_desktop_parity.py` (export and `--check`, per `contracts/parity-fixture.md`) (T012 passes)
- [ ] T018 [US1] With the dataset and the three models, run the export to write `app/test/fixtures/desktop_parity.json`; commit it
- [ ] T019 [US1] Run T013 on each desktop OS and record the result in `docs/evaluation-record.md`. If any pair differs, carry out research R2's fallback (libjpeg-turbo through `dart:ffi` behind `app/lib/inference/decode.dart`) as a new task and re-run
- [ ] T020 [US1] Time a count with the default model on the reference laptop (median of 10) and record it against SC-002 in `docs/evaluation-record.md`

**Checkpoint**: User Story 1 works on its own: the desktop MVP.

---

## Phase 4: User Story 2 - Keep and revisit past counts (Priority: P2)

**Goal**: Past counts listed, reopened, copied to the clipboard, and shown in their folder.

**Independent Test**: Count two photos, restart, both are listed newest first and reopen with the same numbers and flags.

### Tests for User Story 2 ⚠️

- [ ] T021 [P] [US2] Unit test: `ClipboardSharer.share` puts the exact summary text on the clipboard, including the demo-model banner text for a non-default model, in `app/test/desktop_services_test.dart`
- [ ] T022 [P] [US2] Unit test: `FolderRevealer` builds the right command per OS (`explorer /select,`, `open -R`, `xdg-open` on the parent) without running it, in `app/test/desktop_services_test.dart`
- [ ] T023 [P] [US2] Widget test: on desktop the result screen shows "Copy the counts" and "Show in folder", a copy confirmation, and the photo after the original file is deleted, in `app/test/desktop_result_test.dart`

### Implementation for User Story 2

- [ ] T024 [P] [US2] Implement `ClipboardSharer` in `app/lib/app/desktop_services.dart` (T021 passes)
- [ ] T025 [P] [US2] Implement `FolderRevealer` per OS in `app/lib/app/desktop_services.dart` (T022 passes)
- [ ] T026 [US2] Show "Copy the counts" and "Show in folder" on desktop in `app/lib/ui/result_screen.dart` (T023 passes)

**Checkpoint**: User Stories 1 and 2 both work on their own.

---

## Phase 5: User Story 3 - Choose and manage models (Priority: P3)

**Goal**: Download, import, switch and delete models on a computer with the same checks and banners as the phone.

**Independent Test**: Download a second published model, switch to it, count and see the banner; switch back; delete it.

### Tests for User Story 3 ⚠️

- [ ] T027 [P] [US3] Widget test: on desktop, Settings lists models with the do-nothing baseline, marks "Installed"/"In use", imports via the file chooser, refuses to delete the default model and falls back to the default after deleting the active one, in `app/test/desktop_settings_test.dart`
- [ ] T028 [P] [US3] Test that a failed or cancelled download on desktop leaves no `.part` file under the desktop data folder and keeps the active model, in `app/test/desktop_settings_test.dart`

### Implementation for User Story 3

- [ ] T029 [US3] Implement the desktop `ModelFilePicker` (`file_selector`, `.json` then `.onnx`) in `app/lib/app/desktop_services.dart` and wire it in `app/lib/main.dart` (T027 passes)
- [ ] T030 [US3] Adjust any phone-only wording in `app/lib/ui/settings_screen.dart` to the desktop strings from T016 (T027, T028 pass)

**Checkpoint**: User Stories 1–3 work on their own.

---

## Phase 6: User Story 4 - Compare models on one photo (Priority: P4)

**Goal**: One photo, every installed model, one loaded at a time, nothing saved.

**Independent Test**: With two models installed, compare one photo: one row per model, nothing added to history.

- [ ] T031 [P] [US4] Widget test: on desktop, Compare accepts a chosen or dropped photo, shows a row per model, leaves history and the active model unchanged, in `app/test/desktop_compare_test.dart`
- [ ] T032 [US4] Accept a dropped photo in `app/lib/ui/compare_screen.dart` (T031 passes)

**Checkpoint**: User Stories 1–4 work on their own.

---

## Phase 7: User Story 5 - Use the app in Filipino (Priority: P5)

**Goal**: Language follows the system on first start and can be changed in Settings.

**Independent Test**: Set Filipino in Settings: every screen in Filipino, choice remembered after restart.

- [ ] T033 [P] [US5] Unit tests for `SettingsStore` (read, write through `.tmp` and rename, absent means system) and for the system-locale rule (`fil` or `tl` → Filipino) in `app/test/settings_store_test.dart`
- [ ] T034 [P] [US5] Widget test: picking a language in Settings switches the app at once and survives a restart, in `app/test/desktop_settings_test.dart`
- [ ] T035 [US5] Implement `SettingsStore` in `app/lib/app/settings_store.dart` (T033 passes)
- [ ] T036 [US5] Add the Language setting to `app/lib/ui/settings_screen.dart` and pass the locale to `RicePestApp` from `app/lib/main.dart` (T034 passes)

**Checkpoint**: All user stories work on their own.

---

## Phase 8: Polish & Cross-Cutting Concerns

- [ ] T037 [P] Add a desktop build job per OS (build only, plus `flutter test`) and `python -m tools.export_desktop_parity --check` to `.github/workflows/tests.yml`
- [ ] T038 [P] Add a release job that zips the three desktop builds and attaches them to `app-v*` releases in `.github/workflows/build-apk.yml` (or a sibling workflow)
- [ ] T039 [P] Document the desktop app (run, build, data folder, unsigned-build notes) in `README.md` and `docs/setup.md`
- [ ] T040 Check every edge case in `spec.md` by hand on one OS and record the results in `docs/evaluation-record.md` (SC-004)
- [ ] T041 Confirm with a network monitor that a counting session makes no request except a user-started download (SC-005); record it
- [ ] T042 Run `quickstart.md` from a fresh clone on each OS; fix anything it misses

---

## Dependencies & Execution Order

### Phase dependencies

- **Setup (Phase 1)** → **Foundational (Phase 2)** → user stories.
- **User stories (Phases 3–7)** depend only on Phase 2. In priority order: US1 → US2 → US3 → US4 → US5. US4 also uses the model switching from US3 to have two models installed, but can be tested with models placed by hand.
- **Polish (Phase 8)** after the stories it documents or builds.

### Within each story

- Tests first, failing for the right reason (Principle III).
- Services before the screens that use them.
- Each story ends with the whole `flutter test` suite green and a commit.

### Parallel opportunities

- T003 with T002; T005 with T006.
- US1: T010, T011, T012 together; then T014, T016, T017 together.
- US2: T021, T022, T023 together; then T024 and T025 together.
- Once Phase 2 is done, US2, US3 and US5 can proceed in parallel with US1 if more than one person is working.

## Parallel example: User Story 1

```text
Task: "T010 Unit tests for DesktopPhotoSource.fromFile in app/test/desktop_services_test.dart"
Task: "T011 Widget test for the desktop home screen in app/test/desktop_home_test.dart"
Task: "T012 Python tests for tools/export_desktop_parity.py in tests/test_export_desktop_parity.py"
```

## Implementation Strategy

### MVP first (User Story 1 only)

1. Phase 1 and Phase 2.
2. Phase 3 (US1), including the parity run (T019): **stop and validate** SC-001 and SC-002 before going further, because a JPEG-decoding mismatch changes the plan (research R2).
3. Show it: the desktop counts a photo with the published model.

### Incremental delivery

US1 → US2 (history, copy) → US3 (models) → US4 (compare) → US5 (language), each a commit with green tests and a short demo.
