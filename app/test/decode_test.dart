import 'dart:typed_data';

import 'package:flutter_test/flutter_test.dart';
import 'package:image/image.dart' as img;
import 'package:rice_pest_app/inference/decode.dart';
import 'package:rice_pest_app/inference/preprocess.dart';

/// 64x40 image in four flat quadrants, so lossy JPEG keeps each quadrant's centre colour.
const quadrants = [[200, 30, 10], [10, 200, 30], [30, 10, 200], [220, 220, 40]];

RgbImage quadrantRgb() {
  const w = 64, h = 40;
  final px = Uint8List(w * h * 3);
  for (var y = 0; y < h; y++) {
    for (var x = 0; x < w; x++) {
      final q = quadrants[(y < h ~/ 2 ? 0 : 2) + (x < w ~/ 2 ? 0 : 1)];
      px.setRange((y * w + x) * 3, (y * w + x) * 3 + 3, q);
    }
  }
  return RgbImage(w, h, px);
}

List<int> jpegWithOrientation(RgbImage rgb, int orientation) {
  final im = img.Image.fromBytes(width: rgb.width, height: rgb.height, bytes: rgb.pixels.buffer,
      numChannels: 3, order: img.ChannelOrder.rgb);
  im.exif.imageIfd.orientation = orientation;
  return img.encodeJpg(im, quality: 100);
}

List<int> centre(RgbImage im, int qx, int qy) {
  final x = im.width * (2 * qx + 1) ~/ 4, y = im.height * (2 * qy + 1) ~/ 4, i = (y * im.width + x) * 3;
  return im.pixels.sublist(i, i + 3);
}

void main() {
  test('decodePhoto returns the photo upright, matching Pillow exif_transpose for tags 1-8', () {
    final src = quadrantRgb();
    for (var k = 1; k <= 8; k++) {
      final got = decodePhoto(jpegWithOrientation(src, k));
      final want = applyExifOrientation(src, k); // validated against Pillow in contract_test
      expect([got.image.width, got.image.height], [want.width, want.height], reason: 'tag $k size');
      expect(got.orientationTag, k);
      for (final (qx, qy) in [(0, 0), (1, 0), (0, 1), (1, 1)]) {
        final g = centre(got.image, qx, qy), w = centre(want, qx, qy);
        for (var c = 0; c < 3; c++) {
          expect(g[c], closeTo(w[c], 6), reason: 'tag $k quadrant ($qx,$qy) channel $c');
        }
      }
    }
  });

  test('photos without EXIF are upright as-is; RGBA and grey become RGB', () {
    final rgba = img.Image(width: 33, height: 34, numChannels: 4);
    img.fill(rgba, color: img.ColorRgba8(1, 2, 3, 255));
    final a = decodePhoto(img.encodePng(rgba));
    expect(a.orientationTag, 1);
    expect([a.image.width, a.image.height], [33, 34]);
    expect(a.image.pixels.sublist(0, 3), [1, 2, 3]);
    final grey = img.Image(width: 33, height: 34, numChannels: 1);
    for (final p in grey) {
      p.r = 77;
    }
    expect(decodePhoto(img.encodePng(grey)).image.pixels.sublist(0, 3), [77, 77, 77]);
  });

  test('unreadable bytes raise PhotoUnreadable', () {
    expect(() => decodePhoto([1, 2, 3]), throwsA(isA<PhotoUnreadable>()));
  });
}
