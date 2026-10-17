// Golden tests: the app must reproduce the Python reference (rice_pest_detector/infer.py) exactly.
// Fixtures come from `python -m tools.export_app_fixtures`; no photos are stored, only patterns.
import 'dart:convert';
import 'dart:io';
import 'dart:typed_data';

import 'package:crypto/crypto.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:rice_pest_app/inference/contract.dart';
import 'package:rice_pest_app/inference/postprocess.dart';
import 'package:rice_pest_app/inference/preprocess.dart';

/// Same formula as tools/export_app_fixtures.py: (x*7 + y*13 + c*101 + (x*y) % 31) % 256.
RgbImage pattern(int w, int h) {
  final px = Uint8List(w * h * 3);
  for (var y = 0; y < h; y++) {
    for (var x = 0; x < w; x++) {
      for (var c = 0; c < 3; c++) {
        px[(y * w + x) * 3 + c] = (x * 7 + y * 13 + c * 101 + (x * y) % 31) % 256;
      }
    }
  }
  return RgbImage(w, h, px);
}

void main() {
  final fx = jsonDecode(File('test/fixtures/contract_fixtures.json').readAsStringSync())
      as Map<String, dynamic>;

  test('contract constants match the Python package', () {
    final c = fx['contract'] as Map<String, dynamic>;
    expect(c['input_size'], inputSize);
    expect(c['threshold'], defaultThreshold);
    expect(c['class_names'], classNames);
    final species = (c['species_of_class'] as Map<String, dynamic>)
        .map((k, v) => MapEntry(int.parse(k), v as String));
    expect(species, speciesOfClass);
  });

  test('EXIF orientations 1-8 match Pillow exif_transpose', () {
    for (final c in (fx['orientation_cases'] as List).cast<Map<String, dynamic>>()) {
      final out = applyExifOrientation(pattern(c['width'], c['height']), c['orientation']);
      expect([out.width, out.height], [c['out_width'], c['out_height']],
          reason: 'orientation ${c['orientation']} size');
      expect(out.pixels, base64Decode(c['out_rgb_b64']),
          reason: 'orientation ${c['orientation']} pixels');
    }
  });

  test('640x640 bilinear resize is byte-identical to Pillow', () {
    for (final c in (fx['resize_cases'] as List).cast<Map<String, dynamic>>()) {
      final out = resizeBilinear(pattern(c['width'], c['height']), inputSize, inputSize);
      for (final s in (c['samples'] as List).cast<List>()) {
        final i = (s[1] * inputSize + s[0]) * 3;
        expect(out.pixels.sublist(i, i + 3), [s[2], s[3], s[4]],
            reason: '${c['width']}x${c['height']} pixel (${s[0]},${s[1]})');
      }
      expect(sha256.convert(out.pixels).toString(), c['resized_sha256'],
          reason: '${c['width']}x${c['height']} full image');
    }
  });

  test('toTensor is NCHW float32 scaled by 1/255', () {
    final img = RgbImage(2, 1, Uint8List.fromList([255, 0, 51, 102, 153, 204]));
    final t = toTensor(img);
    expect(t.length, 6);
    // channel R: pixels (0,0),(1,0); then G; then B
    expect(t, [1.0, 102 / 255, 0.0, 153 / 255, 51 / 255, 204 / 255].map((v) => closeTo(v, 1e-7)));
  });

  test('photos under 32 px a side are rejected (Pillow parity is not guaranteed there)', () {
    expect(() => preprocess(pattern(31, 600)), throwsA(isA<PhotoTooSmall>()));
    expect(() => preprocess(pattern(600, 31)), throwsA(isA<PhotoTooSmall>()));
    expect(preprocess(pattern(32, 32)).length, 3 * inputSize * inputSize);
  });

  test('preprocess = orientation, resize to 640, tensor', () {
    final t = preprocess(pattern(37, 48), orientation: 6);
    expect(t.length, 3 * inputSize * inputSize);
  });

  test('a model with another input size (576, RF-DETR-M) is resized byte-identically to Pillow too', () {
    final rf = jsonDecode(File('test/fixtures/resize_fixtures.json').readAsStringSync()) as Map<String, dynamic>;
    final cases = (rf['resize_cases'] as List).cast<Map<String, dynamic>>();
    expect(cases.map((c) => c['size']).toSet(), {576});
    for (final c in cases) {
      final size = c['size'] as int;
      final out = resizeBilinear(pattern(c['width'], c['height']), size, size);
      for (final s in (c['samples'] as List).cast<List>()) {
        final i = (s[1] * size + s[0]) * 3;
        expect(out.pixels.sublist(i, i + 3), [s[2], s[3], s[4]],
            reason: '${c['width']}x${c['height']} -> $size pixel (${s[0]},${s[1]})');
      }
      expect(sha256.convert(out.pixels).toString(), c['resized_sha256'],
          reason: '${c['width']}x${c['height']} -> $size full image');
    }
  });

  test('preprocess uses the model input size: 576 and 640', () {
    expect(preprocess(pattern(37, 48), size: 576).length, 3 * 576 * 576);
    expect(preprocess(pattern(37, 48), size: 640).length, 3 * 640 * 640);
    expect(preprocess(pattern(37, 48)).length, 3 * inputSize * inputSize, reason: 'default stays the contract 640');
    final img = pattern(1000, 700);
    expect(preprocess(img, size: 576), toTensor(resizeBilinear(img, 576, 576)));
  });

  test('postprocess matches the reference, including the 0.5 boundary', () {
    var boundary = false;
    for (final c in (fx['postprocess_cases'] as List).cast<Map<String, dynamic>>()) {
      final logits = Float32List.fromList(
          (c['logits'] as List).expand((r) => (r as List).cast<num>()).map((v) => v.toDouble()).toList());
      final boxes = Float32List.fromList(
          (c['pred_boxes'] as List).expand((r) => (r as List).cast<num>()).map((v) => v.toDouble()).toList());
      final got = postprocess(logits, boxes, c['width'], c['height'], threshold: c['threshold']);
      final want = (c['expected'] as List).cast<Map<String, dynamic>>();
      expect(got.length, want.length, reason: c['name']);
      for (var i = 0; i < want.length; i++) {
        final g = got[i], w = want[i];
        expect(g.classId, w['class_id'], reason: '${c['name']} #$i class');
        expect(g.species, w['species']);
        expect(g.score, closeTo(w['score'], 1e-12));
        expect([g.x0, g.y0, g.x1, g.y1].map((v) => v), [
          closeTo(w['x0'], 1e-9), closeTo(w['y0'], 1e-9), closeTo(w['x1'], 1e-9), closeTo(w['y1'], 1e-9)
        ]);
        boundary |= w['score'] == 0.5;
      }
    }
    expect(boundary, isTrue, reason: 'a detection scored exactly 0.5 must be kept');
  });
}
