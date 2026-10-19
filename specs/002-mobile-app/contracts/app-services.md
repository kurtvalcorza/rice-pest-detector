# Contract: app services

The screens depend only on the interfaces in `app/lib/app/services.dart` (plus `Detector` in `app/lib/inference/detector.dart` and `History` in `app/lib/storage/history.dart`). `app/lib/main.dart` wires the real implementations; tests wire fakes. The desktop app ([003-desktop-app](../../003-desktop-app/contracts/desktop-services.md)) supplies its own implementations of the same interfaces.

## PhotoSource

```dart
abstract class PhotoSource {
  Future<PhotoRef?> camera();
  Future<PhotoRef?> gallery();
}
```

- Real: `ImagePickerSource` (`platform_services.dart`). Picks with `image_picker`, with no resize or quality options, then copies the file to `photos/trap-<ms><ext>` and returns a `PhotoRef(name, path)` to the copy.
- `null` means the user cancelled; the screen does nothing.

## Detector

```dart
abstract class Detector {
  String get modelId;                               // shown on results, stored in history
  Future<List<Detection>> detect(PhotoRef photo);   // all detections >= the floor, sorted by score
}
```

- Real: `OnnxDetector.fromFile(path, modelId:, inputSize:)` (`onnx_detector.dart`); `close()` frees the session.
- Fake: `FakeDetector.fromJson` replays recorded detections by photo name.
- Throws `PhotoUnreadable` or `PhotoTooSmall`; the screen shows a message and saves nothing.

## Sharer

```dart
abstract class Sharer {
  Future<void> share(String text, {String? photoPath});
}
```

- Real: `SharePlusSharer` opens the Android share sheet with the text and the photo, if the file exists.
- `text` is `shareSummary` from the strings, prefixed with the not-validated banner text when the record's `notValidated` is true.

## History

```dart
abstract class History {
  Future<List<HistoryEntry>> load();   // newest first
  Future<void> add(HistoryEntry entry);
  Future<void> delete(String id);      // also deletes the photo copy
}
```

Real: `HistoryStore` (`history/history.json`). Format in [data-model.md](../data-model.md).

## ModelCatalog

```dart
abstract class ModelCatalog {
  Future<List<InstalledModel>> list();
  Future<void> activate(String? id);              // null: fall back to the default
  Future<void> delete(String id);                 // never the default
  Future<InstalledModel> importFrom({required File model, required File manifest});
  List<PublishedModel> get published;             // from assets/model_catalog.json
  Future<InstalledModel> download(PublishedModel model,
      {void Function(int received, int? total)? onProgress, DownloadCancel? cancel});
  Future<Detector> open(InstalledModel model);
  Future<void> close(Detector detector);
}
```

- Real: `LocalModelCatalog` (`model_catalog.dart`) over `ModelRegistry`, the pin and the side-load.
- `importFrom` and `download` never change the active model. They throw `ModelImportFailed(reason, detail)` with one of `manifestInvalid`, `sizeMismatch`, `checksumMismatch`, `shapeMismatch`, `selfTestFailed`, `alreadyInstalled`, `unreadable`; `download` also throws `ModelDownloadFailed` (network) or `DownloadCancelled`. Any failure leaves no files.
- The session check is `checkModel(OnnxProbe(), path, manifest)` (`model_check.dart`): input `pixel_values` `[1, 3, S, S]` (a negative batch dimension is accepted), outputs `logits` `[1, 300, num_classes]` and `pred_boxes` `[1, 300, 4]`, then one run on a 64 × 48 synthetic pattern whose outputs must have the right length and only finite values.

## ModelFilePicker

```dart
abstract class ModelFilePicker {
  Future<File?> pickManifest();
  Future<File?> pickModel();
}
```

Real: `FileSelectorModelFiles`, the system file picker with no type filter (Android has no MIME type for `.onnx`; the registry checks the contents). Never a URL.

## AppServices

Holds the above plus the start-up choice: `mode` (`none`, `demo`, `published`), `threshold`, `reviewBelow`, `activeModel`, an optional `download` (the pinned model, offered when not installed), `release` (frees the detector when the services are replaced), and injectable `now` and `newId` for tests. Invariant: a `detector` exactly when `mode != none`. `notValidated` is true when an active model exists and is not the default.

`RicePestApp` (`app.dart`) rebuilds `AppServices` through `reload` after a download, a switch or a delete. The new model is loaded before the old one is freed, so a failed load leaves the app working.
