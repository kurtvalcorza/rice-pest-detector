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

  test('a photo declaring more than maxPhotoPixels is refused before it is decoded', () {
    // A real 1x1 PNG whose header claims 8000x8000; decoding it would need hundreds of MB.
    final png = Uint8List.fromList(img.encodePng(img.Image(width: 1, height: 1)));
    final header = ByteData.sublistView(png, 16, 24)..setUint32(0, 8000)..setUint32(4, 8000);
    ByteData.sublistView(png, 29, 33).setUint32(0, _crc32(png.sublist(12, 29)));
    expect(header.getUint32(0), 8000);
    expect(() => decodePhoto(png),
        throwsA(isA<PhotoTooLarge>().having((e) => [e.width, e.height], 'size', [8000, 8000])));
  });

  test('an image whose header gives no size is refused without decoding what it wraps', () {
    // An ICO holding one PNG: the ICO header reports 0x0, whatever the PNG inside declares.
    final png = img.encodePng(img.Image(width: 1, height: 1));
    final ico = ByteData(22)
      ..setUint16(2, 1, Endian.little) // icon
      ..setUint16(4, 1, Endian.little) // one image
      ..setUint16(10, 1, Endian.little)
      ..setUint16(12, 32, Endian.little)
      ..setUint32(14, png.length, Endian.little)
      ..setUint32(18, 22, Endian.little);
    final data = [...ico.buffer.asUint8List(), ...png];
    expect(img.findDecoderForData(Uint8List.fromList(data))!.startDecode(Uint8List.fromList(data))!.width, 0);
    expect(() => decodePhoto(data), throwsA(isA<PhotoUnreadable>()));
  });

  test('only the first frame of an animated image is decoded', () {
    final anim = img.Image(width: 40, height: 30)..clear(img.ColorRgb8(250, 0, 0));
    anim.addFrame(img.Image(width: 40, height: 30)..clear(img.ColorRgb8(0, 0, 250)));
    final gif = img.encodeGif(anim);
    expect(img.decodeImage(gif)!.numFrames, 2);
    // A pixel budget that fits one frame but not two: decoding every frame would throw.
    final budget = img.Decoder.defaultMaxPixels;
    img.Decoder.defaultMaxPixels = 40 * 30 + 1;
    addTearDown(() => img.Decoder.defaultMaxPixels = budget);
    final first = decodePhoto(gif).image;
    expect([first.width, first.height], [40, 30]);
    expect(first.pixels[0], greaterThan(200));
    expect(first.pixels[2], lessThan(50));
  });
}

int _crc32(List<int> bytes) {
  var c = 0xffffffff;
  for (final b in bytes) {
    c ^= b;
    for (var k = 0; k < 8; k++) {
      c = c & 1 == 1 ? 0xedb88320 ^ (c >> 1) : c >> 1;
    }
  }
  return c ^ 0xffffffff;
}
