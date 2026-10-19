# Quickstart: Desktop Trap Pest Counter

How to build, run and check the desktop app once the tasks are done. Toolchain: Flutter 3.47.7 stable, plus each OS's desktop build tools (Visual Studio 2022 with "Desktop development with C++" on Windows; Xcode on macOS 14+; `clang`, `cmake`, `ninja-build`, `pkg-config` and `libgtk-3-dev` on Linux).

## Run it

```bash
cd app
flutter pub get
flutter run -d windows     # or: -d macos, -d linux
```

1. The home screen says no model is installed. Click **Download the model** and wait for it to finish (172 MB).
2. Click **Choose a photo** and pick a light-trap photo, or drop one onto the window.
3. The result shows both counts, the model and its threshold, and the experimental notice. Click **Copy the counts** and paste somewhere to see the summary.

## Check it

```bash
cd app
flutter test                                  # all unit and widget tests, any OS
```

```bash
python -m tools.export_desktop_parity --check # the parity reference is up to date
```

```bash
cd app
RPD_PARITY_PHOTOS=<folder with the dataset's validation images> flutter test integration_test/desktop_parity_test.dart -d linux
```

The last one needs the dataset's validation images (the dataset is downloaded from Zenodo and checked against `data/split_manifest.json`; see the README's data pipeline) and the three published models installed in the app; otherwise it is skipped.

## Build an installer

```bash
cd app
flutter build windows      # build/windows/x64/runner/Release/
flutter build macos        # build/macos/Build/Products/Release/
flutter build linux        # build/linux/x64/release/bundle/
```

Zip the output folder. The builds are unsigned (spec Assumptions): on macOS, right-click the app and choose Open the first time.
