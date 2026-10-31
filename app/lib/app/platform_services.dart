// Real implementations of the service interfaces (camera/gallery via image_picker, the Android
// share sheet via share_plus). Picked photos are copied into app-private storage so history keeps
// them even if the gallery copy is deleted; nothing leaves the phone unless the user shares.
import 'dart:io';

import 'package:image_picker/image_picker.dart';
import 'package:share_plus/share_plus.dart';

import '../inference/detector.dart';
import 'services.dart';

class ImagePickerSource implements PhotoSource {
  ImagePickerSource(this.photoDir, {ImagePicker? picker}) : _picker = picker ?? ImagePicker();
  final Directory photoDir;
  final ImagePicker _picker;

  @override
  Future<PhotoRef?> camera() => _pick(ImageSource.camera);
  @override
  Future<PhotoRef?> gallery() => _pick(ImageSource.gallery);

  Future<PhotoRef?> _pick(ImageSource source) async {
    // No maxWidth/imageQuality: resizing or recompressing here would change what the model sees.
    final picked = await _picker.pickImage(source: source, requestFullMetadata: true);
    if (picked == null) return null;
    await photoDir.create(recursive: true);
    final ext = picked.name.contains('.') ? picked.name.substring(picked.name.lastIndexOf('.')) : '.jpg';
    final name = 'trap-${DateTime.now().millisecondsSinceEpoch}$ext';
    final saved = await File(picked.path).copy('${photoDir.path}${Platform.pathSeparator}$name');
    return PhotoRef(name, saved.path);
  }

  @override
  Future<void> discard(PhotoRef photo) async {
    final path = photo.path;
    // Only copies this source made: a path outside the app's photo folder is never deleted.
    if (path == null || File(path).parent.absolute.path != photoDir.absolute.path) return;
    try {
      final f = File(path);
      if (await f.exists()) await f.delete();
    } on FileSystemException {
      // Best effort: a leftover copy stays in app-private storage only.
    }
  }
}

class SharePlusSharer implements Sharer {
  @override
  Future<void> share(String text, {String? photoPath}) async {
    await SharePlus.instance.share(ShareParams(
        text: text, files: photoPath != null && File(photoPath).existsSync() ? [XFile(photoPath)] : null));
  }
}
