---
title: "Rice-pest detector demo app — MVP plan (design)"
date: 2026-10-15
status: approved 2026-10-15
note: "Later changes: demo threshold 0.04, low-confidence flag below 0.06 and the bundled test model removed. From 2026-10-17 (model r50-v5): demo threshold 0.48, flag below 0.64. From 2026-10-18: weights published on Kaggle; a per-model registry (download list, import checks, Compare screen, not-validated banner); history kept as one JSON file, not SQLite; the data credit is in NOTICE; the release gates are those in the README (model and weights met; field validation, wording review, data protection and phone latency open)."
---


# Rice-pest detector demo app — MVP plan

> **Note (18 Oct 2026).** This is the historical design brief, kept as written. The app was first briefed (15 Oct 2026) as a tool for farmers. The project has since been scoped as a teaching demonstration: the app is not made for farmers, is not official and has not been validated in the field. Where this brief mentions farmers, agricultural technicians, pilot sites or a DPO review, it records the original brief, not the current scope; the app's share button reads "Share the counts". Later design changes are listed in the `note` field above.

## Context

The owner wants a rice-pest detector app for **farmers on phones**. The detector (RT-DETR-r18vd, trained on the open Deleña et al. dataset) is not ready:
- Run r18-1 keeps zero detections at the 0.5 threshold, so its count accuracy (0.456) equals what a model predicting nothing would score.
- Two of the four sex classes are below 0.70 mAP50, so the app reports species only.
- No ONNX export existed yet when this was written.

The model card currently rules out **farmer phone photos** ("Images from other trap designs, cameras or crops") and **decisions made without expert review**. The MVP is therefore built now against a fake detector and the fixed inference contract. Real counts reach farmers only after the model and field-validation gates in §6 are passed.

Decided with the owner (2026-10-15):
- **Users:** farmers on Android phones.
- **Scope:** MVP built while the model is fixed.
- **Output:** counts plus "share with your agricultural technician"; no spray or treatment advice.
- **Framework:** Flutter with ONNX Runtime on the device.
- **Languages:** Filipino and English, plus regional languages for the pilot sites.
- **Photos:** stay on the device; sharing happens only when the farmer chooses it.
- **Code location:** inside this repository (an `app/` folder), so the model and app are versioned together.

## Approach

### 1. Where the code lives

- `rice-pest-detector/app/`: a Flutter project for Android first.
- `rice-pest-detector/tools/export_app_fixtures.py` (new): uses the existing `src/rice_pest_detector/infer.py` to write golden files for the app's parity tests: the preprocessed tensor checksums, raw model outputs and expected detections for about 10 sample images. Sample images are CC BY 4.0 and carry the full attribution.
- The app reuses `docs/inference-contract.md` as its specification. Any change to the contract must update `infer.py` and the app together.

### 2. App structure (`app/lib/`)

| Module | Role | Mirrors |
|---|---|---|
| `inference/preprocess.dart` | EXIF rotate → RGB → **PIL-equivalent bilinear** resize to 640×640, no letterbox → ÷255 → NCHW float32 `(1,3,640,640)` | `infer.preprocess` |
| `inference/postprocess.dart` | Sigmoid of `logits (1,300,4)` → max over classes, argmax for the class → keep when `score >= threshold` → boxes from `pred_boxes`, sized to the image *after* EXIF rotation → sorted by score; **species only** | `infer.postprocess`, `SPECIES_OF_CLASS` |
| `inference/detector.dart` | `Detector` interface; `FakeDetector` replays recorded model outputs; `OnnxDetector` uses the ONNX Runtime Flutter binding with input `pixel_values` and outputs `logits`, `pred_boxes` | — |
| `counting/` | Species counts per photo; review flags (low-confidence detections, or more than 30 counted = "crowded tray"); history | — |
| `model/` | Download the model on first run with a SHA-256 pin, a `.part` file, and an option to load it from local storage. In MVP builds only the bundled test model ships. | — |
| `ui/` | Take or pick a photo → result screen (counts per species, boxes drawn on the photo, review flags, model version and threshold) → history → **Share with technician** through the Android share sheet (text summary, photo optional) | — |
| `storage/` | Local SQLite for history; photos kept in app-private storage; delete from the app | — |
| `l10n/` | Flutter `gen-l10n` ARB files: `fil` and `en` first; regional ARBs added per pilot site and checked by native speakers | — |
| `about/` | Licences (Apache-2.0 for the code and model; CC BY 4.0 data citation with the changes statement), the model's intended use and limits, and the privacy notice | `DATA_LICENSE.txt`, model card |

The app makes no network calls except the explicit model download. It has no analytics.

The wording for counts and referrals has these rules:
- Say "possible", never diagnose.
- Never recommend a treatment.
- Always offer "share with your technician".
- Show the illustrative-model notice until the release gates are passed.

### 3. MVP build order (each step tested before the next)

1. **Scaffold and contract tests:** Flutter project, ARB setup, `Detector` interface, `FakeDetector`.
2. **Post-processing:** Dart tests built from a tiny constant test model's outputs. These cover the score threshold, sorting, sizing boxes after EXIF rotation, and species mapping.
3. **Pre-processing parity:** a PIL-equivalent bilinear resize, tested against the golden tensors from `export_app_fixtures.py`. Bitmap scaling on Android does not match PIL, so this step makes or breaks the app.
4. **On-device ONNX:** run the bundled `tiny_model` ONNX through ONNX Runtime and check that its outputs match the fixtures exactly.
5. **Counting and review flags:** port the counting and review rules, with unit tests for each.
6. **UI and history:** the photo flow, result screen, history list and share sheet. No treatment wording anywhere.
7. **Localisation:** Filipino and English complete; the regional-language mechanism ready.
8. **Model download:** pin checking and a local-file option. Tested with the tiny model, since the real one is not published.
9. **Device test:** install a debug build on a low-end Android phone and measure startup, memory and latency on the tiny model.

### 4. Reuse, not rewrite

- **Contract:** `rice-pest-detector/src/rice_pest_detector/infer.py`, `docs/inference-contract.md`.
- **Classes:** `rice_pest_detector/__init__.py` (`CLASS_NAMES`, `SPECIES_OF_CLASS`).
- **Test model:** a tiny constant ONNX model, so tests run without the real weights.
- **Model pinning:** a SHA-256 pin file checked before the model loads.
- **Metric definitions for field validation:** `rice-pest-detector/src/rice_pest_detector/metrics.py` (`count_errors`, `count_accuracy`).

### 5. Out of scope for the MVP

iOS, any server or photo upload, per-sex counts, trends and maps across sites, treatment advice, and publishing the app or the weights.

### 6. Release gates before any farmer sees real counts (owner-held)

1. **Model:** passes spec §6 with a threshold chosen on validation data; ONNX export and the parity test done.
2. **Field validation on phone photos:** a new, consented set of farmer phone photos, labelled by experts and measured with `count_errors`. This is needed because phone photos are outside the current intended use; the model card would be updated afterwards.
3. **Shipping the weights:** owner approval to put the weights in an app, which counts as publishing under spec §8, plus the hosting choice.
4. **Referral flow:** reviewed by an agricultural technician or agronomist.
5. **Privacy:** DPO review of the privacy notice; pilot consent forms.
6. **Phone latency target:** owner to set one (proposed: ≤ 5 s per photo on the reference low-end phone, matching the laptop gate).

## Verification

- `python tools/export_app_fixtures.py`, then `flutter test` in `app/`. This runs the unit tests for post-processing (including the score threshold), pre-processing parity against the golden tensors, counting and review flags, model-pin checks and localisation completeness (every key present in `fil` and `en`).
- `flutter test integration_test/` on an Android emulator: photo → result → history → share sheet using the `FakeDetector` fixtures and the bundled tiny ONNX model.
- On a real low-end Android phone: install the debug APK and record latency, memory and APK size in a dated evidence note.
- `pytest` in `rice-pest-detector` still passes (86 tests), since the new tool must not change the package.
- Manual wording review: no screen offers treatment advice, and every result screen offers "share with your technician".
