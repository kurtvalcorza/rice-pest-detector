# Implementation Plan: Desktop Trap Pest Counter

**Branch**: `003-desktop-app` | **Date**: 2026-10-19 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/003-desktop-app/spec.md`

## Summary

Add Windows, macOS and Linux targets to the existing Flutter app in `app/`, so the same code counts rice black bug and white stemborer on a computer. Shared logic (inference contract, counting, manifests, registry, download, history, strings) is reused unchanged. New code is limited to desktop implementations of the existing service interfaces: choose or drop a photo, copy the counts to the clipboard, show a photo in its folder, a per-user data folder, and a language setting. The stack was decided in [research.md](research.md) (R1): Flutter desktop over a Tauri rewrite, because it keeps one implementation of the inference contract (Principles II and VII).

## Technical Context

**Language/Version**: Dart 3.13 with Flutter 3.47.7 (stable), the versions the app and CI already use

**Primary Dependencies**: `flutter_onnxruntime` 1.9.0 (ONNX Runtime 1.28.x on all three desktops), `image`, `file_selector`, `path_provider`, `http`, `crypto` (all existing); `desktop_drop` (new, for drag and drop)

**Storage**: Files in the per-user application-support folder: `models/<id>/` (model + manifest), `photos/` (copies of counted photos), `history/history.json`, `models/active.json`, `settings.json` (new: language)

**Testing**: `flutter test` (unit and widget, host-side, all platforms); `integration_test` on a desktop target for the end-to-end count; `pytest` for the new parity tool

**Target Platform**: Windows 10 and 11 (x64), macOS 14+ (Apple silicon and Intel), Linux x64 (a current GNOME or KDE desktop with GTK 3)

**Project Type**: Desktop app (a new set of targets for an existing mobile app)

**Performance Goals**: A count within 5 s of choosing a photo with the default model on the reference laptop (SC-002; the project's CPU gate measured 1.14 s median)

**Constraints**: No network except a user-started model download (Principle V); one model loaded at a time in Compare; exact counts and flags against the reference on 60 photo-model pairs (SC-001)

**Scale/Scope**: 6 existing screens (home, result, settings, compare, about, plus the not-validated banner); 3 published models; about 5 new desktop service classes and 1 new setting

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Check | Before research | After design |
| :-- | :-- | :-- | :-- |
| I. Teaching demo | Not-validated notice, demo-model banner and the no-treatment-words test are reused as they are; new desktop strings go through the same test | Pass | Pass: desktop ARB keys are covered by `l10n_test.dart` |
| II. One inference contract | The desktop uses the same Dart contract code and golden fixtures; parity on real photos is measured by SC-001 | Pass, with risk R2 (JPEG decoder) | Pass: R2 fallback stays inside `decode.dart`, fixtures unchanged |
| III. Test-first | Each desktop service gets a failing test first; the whole `flutter test` suite must stay green; the new parity tool has `--check` | Pass | Pass: tasks order tests before code |
| IV. Rules fixed before results | Thresholds come from manifests; the 20-photo parity list is chosen by a fixed, seeded rule from validation photos, never test photos | Pass | Pass |
| V. Local and private | Data in the per-user application-support folder; network only through the existing catalogue download | Pass | Pass: no new network code |
| VI. Verified models only | Import and download checks are reused unchanged | Pass | Pass |
| VII. Shared sources, simplest thing | One codebase, existing catalogue, pin, manifests, strings and history format | Pass (Flutter desktop); Tauri would fail this gate | Pass: one new dependency (`desktop_drop`), justified in research R3 |

No violations; Complexity Tracking is empty.

## Project Structure

### Documentation (this feature)

```text
specs/003-desktop-app/
├── plan.md              # This file
├── research.md          # Phase 0: stack decision and unknowns
├── data-model.md        # Phase 1: entities and files
├── quickstart.md        # Phase 1: build, run and verify
├── contracts/
│   ├── desktop-services.md   # Desktop implementations of the app's service interfaces
│   └── parity-fixture.md     # The SC-001 reference file and its tool
├── checklists/
│   └── requirements.md  # Spec quality checklist
└── tasks.md             # Phase 2 (/speckit-tasks)
```

### Source Code (repository root)

```text
app/
├── lib/
│   ├── app/
│   │   ├── services.dart              # PhotoSource gains fromFile(); unchanged otherwise
│   │   ├── platform_services.dart     # phone implementations (unchanged)
│   │   ├── desktop_services.dart      # NEW: file chooser, drop, clipboard sharer, reveal-in-folder
│   │   ├── data_dir.dart              # NEW: per-platform data folder choice
│   │   └── settings_store.dart        # NEW: language setting
│   ├── inference/decode.dart          # unchanged unless R2's fallback is needed
│   ├── l10n/app_en.arb, app_fil.arb   # + desktop-only keys
│   ├── ui/home_screen.dart            # drop target; camera button hidden on desktop
│   ├── ui/result_screen.dart          # "Copy the counts", "Show in folder" on desktop
│   ├── ui/settings_screen.dart        # + Language
│   └── main.dart                      # picks phone or desktop services
├── windows/  macos/  linux/           # NEW: generated by `flutter create --platforms`
├── test/
│   ├── desktop_services_test.dart     # NEW
│   ├── settings_store_test.dart       # NEW
│   └── fixtures/desktop_parity.json   # NEW (generated, R9)
└── integration_test/
    └── desktop_parity_test.dart       # NEW: SC-001, skipped without the photos and models

tools/export_desktop_parity.py         # NEW (R9), with --check
tests/test_export_desktop_parity.py    # NEW
.github/workflows/tests.yml            # + desktop build smoke job per OS, + parity --check
```

**Structure Decision**: Extend the existing `app/` Flutter project with desktop platform folders; no new project. Desktop-only code sits beside the phone implementations behind the interfaces in `app/lib/app/services.dart`, chosen at start-up in `main.dart`.

## Complexity Tracking

No entries: the Constitution Check passes without exceptions.
