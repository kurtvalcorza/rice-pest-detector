# Contract: desktop services

The screens depend only on the interfaces in `app/lib/app/services.dart`. The desktop supplies its own implementations; the screens and shared logic do not change. `main.dart` picks phone or desktop implementations with `Platform.isWindows || Platform.isMacOS || Platform.isLinux`.

## PhotoSource

```dart
abstract class PhotoSource {
  Future<PhotoRef?> camera();          // desktop: never called (button hidden); returns null
  Future<PhotoRef?> gallery();         // desktop: file chooser, filter JPEG and PNG
  Future<PhotoRef?> fromFile(String path); // NEW: used by drag and drop (and by gallery())
}
```

- `fromFile` copies the file into `photos/` under the data folder and returns a `PhotoRef` to the copy (as the phone does for gallery picks).
- Unsupported type, unreadable file or a side under 32 px: throws `PhotoRejected(reason)`; nothing is copied.
- Several files dropped at once: the home screen passes the first to `fromFile` and shows "Only the first photo was used".

## Sharer

```dart
abstract class Sharer {
  Future<void> share(String text, {String? photoPath});
}
```

- Desktop: puts `text` on the clipboard and ignores `photoPath`. The result screen shows the button as "Copy the counts" and a confirmation after copying.
- `text` is built by the existing summary code, so it includes the experimental notice and, for a non-default model, the demo-model banner text (FR-015).

## FolderRevealer (new)

```dart
abstract class FolderRevealer {
  Future<void> reveal(String path);
}
```

- Windows: `explorer /select,<path>`; macOS: `open -R <path>`; Linux: `xdg-open <parent folder>`.
- Phone: not provided (`null` in `AppServices`), and the screen hides the button.

## Data folder

`dataDirectory()` returns `getApplicationSupportDirectory()` on desktop and `getApplicationDocumentsDirectory()` on the phone. Everything else (`models/` with `models/active.json`, `photos/`, `history/history.json`, `settings.json`) is relative to it.

## SettingsStore (new)

```dart
abstract class SettingsStore {
  Future<String?> language();          // "en", "fil" or null (follow the system)
  Future<void> setLanguage(String? code);
}
```

Written through a `.tmp` file and a rename. Used on phone and desktop alike.
