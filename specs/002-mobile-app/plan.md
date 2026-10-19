# Implementation Plan: Trap Pest Counter (phone app)

**Branch**: `002-mobile-app` | **Date**: 2026-10-19 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/002-mobile-app/spec.md`

**Status**: Implemented (Spec Kit record written 2026-10-19). The app was first designed with a brainstorming workflow before Spec Kit was added; this is the Spec Kit record of it. The Constitution Check below is applied after the fact, against constitution v1.0.0.

## Summary

A Flutter app for Android in `app/` that counts rice black bug and white stemborer on a light-trap photo with an ONNX model running on the phone through `flutter_onnxruntime`. The inference contract is ported to Dart and kept identical to the Python reference by golden fixtures (research R3, R4). Screens depend only on small service interfaces in `app/lib/app/services.dart`, so the contract, counting, model checks, history and screens are all tested on the host without a phone (R10). Models are never bundled: the user downloads one, verified by size and SHA-256, or imports one with a strict manifest and an ONNX session self-test (R6–R8). The app was built test-first in milestones: contract, decoding, counting, screens and history, languages, model download, then the model registry, download list and compare screen.

## Technical Context

**Language/Version**: Dart (SDK `^3.13.5`) with Flutter 3.47.7 stable, the version CI uses (`.github/workflows/tests.yml`, `build-apk.yml`)

**Primary Dependencies**: `flutter_onnxruntime` ^1.9.0 (ONNX Runtime 1.28.0 on Android), `image` ^4.12.0 (decoding), `image_picker` ^1.2.4 (camera and gallery), `share_plus` ^13.3.1 (share sheet), `file_selector` ^1.1.0 (import), `path_provider` ^2.1.6, `http` ^1.6.0, `crypto` ^3.0.7, `intl` ^0.20.3 with `flutter_localizations` (`app/pubspec.yaml`)

**Storage**: Files in the app's documents folder (readable only by the app): `models/<id>/` (model, manifest, verification stamp) and `models/active.json`; `model/` (the pinned download); `demo/` (developer side-load); `history/history.json`; `photos/` (copies of counted photos). Details in [data-model.md](data-model.md).

**Testing**: `flutter test` on the host (140 `test`/`testWidgets` declarations in 18 files under `app/test/`); `flutter analyze`; one on-device smoke test through `flutter drive` (`app/integration_test/app_smoke_test.dart`); `pytest` for the fixture generator; `--check` modes for both golden-fixture generators in CI

**Target Platform**: Android phones; release APKs built per CPU type (`--split-per-abi`), arm64-v8a for most phones; `minSdk` is Flutter's default

**Project Type**: Mobile app inside the model repository, so the model and the app are versioned together

**Performance Goals**: A count within 5 s per photo on a reference low-end phone (proposed release gate 6; not yet measured). For scale: r50-v5 takes 1.14 s per photo (median of 10) on the reference laptop CPU (README, "Models")

**Constraints**: Pillow-identical resize (byte for byte on the fixtures); photos at least 32 px a side; no network except a user-started download to a bundled URL; one model loaded at a time in Compare; models of 122–172 MB downloaded on the phone; debug APK about 184 MB (README)

**Scale/Scope**: 5 screens (home, result, settings, compare, about) plus the not-validated banner; 3 published models; 76 strings per language; 2 species

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Check | Before research | After design |
| :-- | :-- | :-- | :-- |
| I. Teaching demo | A notice per model state; a "Not validated" tag on every model and a banner for any non-default model; `app/test/l10n_test.dart` fails on treatment, audience or organisation words | Pass | Pass |
| II. One inference contract | Dart port of `src/rice_pest_detector/infer.py`; golden fixtures from the reference (`tools/export_app_fixtures.py`, `app/tool/export_resize_fixtures.py`) checked in `contract_test.dart` and in CI with `--check` | Pass | Pass, with one gap: the JPEG decoder difference ("a level or two per pixel") is recorded in `decode.dart` and the README but has not been measured on real photos on a phone (open task T037) |
| III. Test-first | Each milestone started with failing tests on the host; `flutter test` and `flutter analyze` in CI; fixture generators have `--check` | Pass | Pass |
| IV. Rules fixed before results | Counting threshold and review level come from each manifest (`threshold`, `review_below`), chosen on validation by the model pipeline; the app has no threshold setting | Pass | Pass |
| V. Local and private | The app's own storage; the only HTTP calls are in `fetchToFile` (`app/lib/model/model_store.dart`), reached only from a Download tap; sharing only through the share sheet | Pass | Pass |
| VI. Verified models only | Registry imports and catalogue downloads check size, SHA-256, input and output names and shapes, and a synthetic self-test; strict manifests | Pass for the registry | **Deviation**: the home-screen pinned download and the developer `demo.json` side-load check size and SHA-256 only, not the session self-test. Justified below; open task T083 |
| VII. Shared sources, simplest thing | Catalogue manifests equal `models/*.manifest.json` (`published_models_test.dart`); the pin equals the default model's catalogue entry (`model_pin_test.dart`); history is one JSON file | Pass | Pass, with the three install routes justified below |

## Project Structure

### Documentation (this feature)

```text
specs/002-mobile-app/
├── plan.md              # This file
├── research.md          # Phase 0: decisions
├── data-model.md        # Phase 1: entities and files
├── quickstart.md        # Phase 1: build, run and verify
├── contracts/
│   ├── inference.md          # The inference contract as the app implements it
│   ├── app-services.md       # The service interfaces in app/lib/app/services.dart
│   └── model-files.md        # Model manifest, catalogue, pin and demo.json formats
├── checklists/
│   └── requirements.md  # Spec quality checklist
└── tasks.md             # Phase 2 (/speckit-tasks)
```

### Source Code (repository root)

```text
app/
├── lib/
│   ├── main.dart                  # wiring: storage folders, pin, catalogue, start-up model choice
│   ├── app/
│   │   ├── app.dart               # RicePestApp: locale, reload after a model change
│   │   ├── bootstrap.dart         # chooseModel, installedModels
│   │   ├── services.dart          # PhotoSource, Sharer, ModelCatalog, ModelFilePicker, AppServices
│   │   ├── platform_services.dart # image_picker source, share_plus sharer
│   │   └── model_catalog.dart     # LocalModelCatalog, file_selector picker
│   ├── inference/                 # contract, decode, preprocess, postprocess, detector, onnx_detector, model_check
│   ├── counting/counting.dart     # species counts, review flags
│   ├── model/                     # model_manifest, published_models, model_registry, model_store
│   ├── storage/history.dart       # HistoryEntry, HistoryStore
│   ├── ui/                        # home, result, settings, compare, about, not-validated banner
│   └── l10n/                      # app_en.arb, app_fil.arb (+ generated)
├── assets/model_pin.json  assets/model_catalog.json
├── test/                          # 18 test files; fixtures/contract_fixtures.json, resize_fixtures.json
├── integration_test/app_smoke_test.dart   test_driver/integration_test.dart
└── tool/export_resize_fixtures.py

tools/export_app_fixtures.py        tests/test_export_app_fixtures.py
models/rice-pest-{r50-v5,rfdetr-m,dfine-l}.manifest.json
.github/workflows/tests.yml  .github/workflows/build-apk.yml
```

**Structure Decision**: One Flutter project in `app/` inside the model repository. Pure Dart logic (`inference/`, `counting/`, `model/`, `storage/`) has no platform plugin in it except at the edges (`onnx_detector.dart`, `platform_services.dart`, `model_catalog.dart`), so it runs under `flutter test` on any computer.

## Complexity Tracking

| Violation | Why needed | Simpler alternative rejected because |
| :-- | :-- | :-- |
| Three install routes: the pinned download (`model/`), the developer side-load (`demo/`) and the registry (`models/<id>/`) | The pin gives a fresh install a one-tap first download from the home screen; the side-load lets a developer test real weights before any were published. The registry came later with import, download list and compare | Removing the older routes would break installs and the README's developer instructions; `installedModels` lists all three as one list and drops duplicates by SHA-256 |
| The pinned download and the side-load skip the ONNX session self-test (Principle VI) | Both are pinned to an exact SHA-256, and the pinned file (r50-v5) passed ONNX-to-PyTorch parity at export | Not fully justified under v1.0.0: open task T083 routes the pinned download through the registry's checks |
