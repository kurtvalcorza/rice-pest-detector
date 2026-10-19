# Quickstart: Trap Pest Counter (phone app)

How to build, run and check the phone app. Toolchain: Flutter 3.47.7 stable and the Android SDK (Flutter breaks on install paths that contain spaces); Python 3.12 with the repository's requirements for the fixture checks. Fuller instructions are in the README, "Demo app (Android)", and `docs/setup.md`.

## Check it (no phone needed)

```bash
cd app
flutter pub get
flutter analyze
flutter test            # 140 host tests: contract, decoding, counting, history, models, strings, screens
```

```bash
python -m tools.export_app_fixtures --check        # golden fixtures at 640 are up to date
python app/tool/export_resize_fixtures.py --check   # golden fixtures at 576 are up to date
```

Each `--check` exits 1 if the committed fixtures differ from a fresh build from the Python reference. Both run in CI (`.github/workflows/tests.yml`).

## Check it on an emulator

```bash
cd app
flutter drive --driver=test_driver/integration_test.dart --target=integration_test/app_smoke_test.dart -d emulator-5554 --no-enable-impeller
```

Expected: the app starts, says no model is installed, and the camera button is disabled. `flutter drive` uninstalls the app afterwards.

## Run it

- Emulator: `.\tools\run_emulator.ps1` (Windows PowerShell) or `tools/run_emulator.sh` (macOS, Linux) starts the first emulator and runs the app; add `-Fresh` / `--fresh` to clear its data first.
- Phone: `flutter run --release -d <device-id>` from `app/`, or install the arm64-v8a APK from `flutter build apk --release --split-per-abi`.

## Walk through the user stories

1. **Count (US1).** On a fresh install the home screen says no model is installed. Tap **Download the model (172 MB)**. When it finishes, the notice changes to the Demo notice. Tap **Choose a photo** and pick a light-trap photo: the result shows both counts, "Model r50-v5 · threshold 0.48" and the experimental notice, plus a review flag if one applies.
2. **History and share (US2).** Go back: the count is listed under **Past counts**. Open it, then tap **Share the counts**: the share sheet opens with the summary and the photo.
3. **Models (US3).** Settings → **Download a model** → download RF-DETR-M. Its row then says **Installed**. Tap it in the **Model** list: the home screen shows the "Demo model, not validated" banner. Tap r50-v5 to switch back; the banner goes. Delete RF-DETR-M (r50-v5 has no delete button).
4. **Compare (US4).** With two models installed, Settings → **Compare models on one photo** → choose a photo: one row per model with counts, flags and time. **Past counts** is unchanged.
5. **Filipino (US5).** Set the phone's language to Filipino and reopen the app.

Expected numbers and formats are in [data-model.md](data-model.md) and [contracts/](contracts/).
