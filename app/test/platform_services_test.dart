import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:rice_pest_app/app/platform_services.dart';
import 'package:rice_pest_app/inference/detector.dart';

void main() {
  late Directory root;
  setUp(() => root = Directory.systemTemp.createTempSync('photo source '));
  tearDown(() => root.deleteSync(recursive: true));

  test('discard deletes a copy in the app photo folder and nothing outside it', () async {
    final photos = Directory('${root.path}${Platform.pathSeparator}photos')..createSync();
    final source = ImagePickerSource(photos);
    final copy = File('${photos.path}${Platform.pathSeparator}trap-1.jpg')..writeAsBytesSync([0]);
    final original = File('${root.path}${Platform.pathSeparator}gallery.jpg')..writeAsBytesSync([0]);
    await source.discard(PhotoRef('trap-1.jpg', copy.path));
    await source.discard(PhotoRef('gallery.jpg', original.path));
    await source.discard(const PhotoRef('no-path.jpg'));
    expect(copy.existsSync(), isFalse);
    expect(original.existsSync(), isTrue, reason: 'a file the picker did not copy is never deleted');
  });
}
