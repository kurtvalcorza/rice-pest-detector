# Research: Desktop Trap Pest Counter

**Feature**: [spec.md](spec.md) | **Plan**: [plan.md](plan.md) | **Date**: 2026-10-19

The stack was left open on purpose ("plan both, decide in research"). This file resolves it and the other unknowns from the Technical Context.

## R1. Stack: Flutter desktop or Tauri 2 (Rust + TypeScript)

**Decision**: Flutter desktop: add Windows, macOS and Linux targets to the existing app in `app/`.

**Rationale**:

- **Principle VII (shared sources, simplest thing).** The phone app already implements every behaviour the spec asks for (inference contract, counting, flags, strict manifests, model registry, download with checks, import, compare, history, English and Filipino), behind service interfaces (`app/lib/app/services.dart`) that keep platform code at the edges. A desktop target reuses all of it. Tauri would need the contract, counting, manifests, registry, history and download rewritten in Rust and every screen rebuilt in TypeScript.
- **Principle II (one inference contract).** One Dart implementation passes the golden fixtures for phone and desktop. A Rust port would be a second implementation that every future contract change must update and test separately.
- **Principle III (test-first).** The existing Flutter suite (about 140 tests) (`flutter test`) cover the shared code on every platform the moment the desktop targets exist; only desktop-specific services need new tests.
- **The runtime is supported.** `flutter_onnxruntime` 1.9.0, the package the app already uses, declares Windows, Linux and macOS plugins. It uses ONNX Runtime 1.28.3 on Windows and Linux (downloaded at build time) and 1.28.0 on macOS, the same minor version as the phone (1.28.0).

**Alternatives considered**:

| Option | For | Against |
| :-- | :-- | :-- |
| Tauri 2, Rust core, TypeScript UI | Small installers; a second, independent client would show that the contract and its fixtures are enough to port the app; the Rust ecosystem makes it easy to use the same JPEG decoder as Pillow | Rewrites about 1,300 lines of tested Dart logic and about 1,200 lines of screens; two clients to keep in step on every contract change; new toolchains (Rust, Node, CMake) for contributors; violates Principle VII without a need the spec states |
| Electron or a web app | Familiar web stack | Larger runtime; ONNX Runtime in a browser differs from native; a web app breaks "photos stay on the computer" unless it is packaged anyway |
| Python desktop (Qt) around the reference `infer.py` | Exact parity for free (it *is* the reference) | Ships PyTorch-free but still a large Python runtime; a third UI with its own strings; no reuse of the app's screens, registry or history |

## R2. JPEG decoding and exact counts (SC-001)

**Decision**: Keep the app's current decoder (`image` package) and measure SC-001 early, in User Story 1. If any of the 60 photo-model pairs differs from the reference, decode JPEGs on desktop with libjpeg-turbo (the decoder Pillow uses) through `dart:ffi`, behind the existing `decode.dart` interface.

**Rationale**: The phone app already records that its JPEG decoder differs from Pillow "by a level or two per pixel", so real-photo parity is detection-level, not byte-level (README, "How parity with Python is kept"). A one-level pixel difference can move a detection that scores right at a threshold across it and change a count. SC-001 asks for 0 differences, so it must be measured, not assumed. The fallback is contained: it changes one function, and the golden fixtures and the measured list protect it.

**Alternatives considered**: Relax SC-001 to detection-level tolerance (rejected: a learner comparing counts with the reference would see a mismatch with no explanation); use libjpeg-turbo from the start (rejected for now: adds a native build dependency that may not be needed).

## R3. Photo input on a desktop

**Decision**: "Choose a photo" uses `file_selector` (already a dependency). Drag and drop uses the `desktop_drop` package; its support for all three desktops is confirmed in the first task that adds it (T006), before any screen depends on it. The phone's camera button is hidden on desktop. The `PhotoSource` interface gains a `fromFile(path)` entry used by both paths; the picked file is copied into the app's data folder, as on the phone.

**Alternatives considered**: Implement drop natively per platform (rejected: three native implementations for one feature).

## R4. Sharing becomes "Copy the counts"

**Decision**: A desktop `Sharer` puts the summary text on the clipboard with Flutter's built-in `Clipboard.setData`; the result screen labels the button "Copy the counts". "Show the photo in its folder" opens the system file manager on the app's copy: `explorer /select,` on Windows, `open -R` on macOS, `xdg-open` on the folder on Linux.

**Alternatives considered**: `share_plus` on desktop (rejected: its desktop behaviour differs per OS and was not checked; copying to the clipboard is predictable everywhere and needs no new dependency).

## R5. Data folder

**Decision**: `getApplicationSupportDirectory()` (from `path_provider`, already a dependency) on desktop, which resolves to the per-user application-data folder on each OS. The phone keeps `getApplicationDocumentsDirectory()`. Layout inside it (`models/`, `photos/`, history file) is unchanged.

**Rationale**: The documents folder on a desktop is the user's visible Documents, which is the wrong place for app-private data (Principle V).

## R6. Language choice

**Decision**: On first start, use Filipino when the system locale's language is `fil` or `tl`, else English. A Language setting stores the choice next to the active-model setting. `RicePestApp` already accepts a `locale`. Desktop-specific wording (for example "computer" instead of "phone", "Copy the counts") goes in new ARB keys used only on desktop, so the phone's strings are unchanged.

## R7. Packaging

**Decision**: Unsigned release builds per OS from CI: a zipped Windows folder (`flutter build windows`), a macOS `.app` in a zip (`flutter build macos`, macOS 14+), and a Linux tarball (`flutter build linux`). Signing, notarisation and auto-update are out of scope (spec Assumptions).

**Note**: macOS 14 is the plugin's minimum (`flutter_onnxruntime` README), so the spec's platform requirement (FR-021) states macOS 14 or later.

## R8. Single instance

**Decision**: No single-instance lock in this version. History and the active-model file are already written through a `.tmp` file and a rename (`lib/storage/history.dart`, `lib/model/model_registry.dart`), so a second copy cannot corrupt them; the edge case in the spec is met by "works without corrupting".

## R9. Reference counts for SC-001

**Decision**: A small tool, `tools/export_desktop_parity.py`, picks 20 validation photos by a fixed rule (seeded, from the committed split), writes their file names and the reference implementation's counts and flags for each of the three published models to `app/test/fixtures/desktop_parity.json`, and has a `--check` mode (Principle III). No photos are committed; an integration test fetches them with the data pipeline and is skipped when they are absent.
