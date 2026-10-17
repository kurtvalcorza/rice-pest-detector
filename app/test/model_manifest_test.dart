// Model manifests are parsed strictly: an imported model is enabled only if its manifest is complete
// and every value is in range.
import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';
import 'package:rice_pest_app/model/model_manifest.dart';

Map<String, dynamic> valid() => {
      'id': 'rfdetr-m',
      'label': 'RF-DETR-M',
      'architecture': 'RF-DETR',
      'base_model': 'Roboflow/rf-detr-medium',
      'licence': 'Apache-2.0',
      'input_size': 576,
      'threshold': 0.48,
      'review_below': 0.63,
      'sha256': '07161f11d2bfc390510627ddff72a8436045b1f79cccd00682f19359fe5c660f',
      'bytes': 121956743,
      'outputs': ['logits', 'pred_boxes'],
      'num_classes': 4,
      'validation': {'count_accuracy': 0.846, 'species_map50': 0.933, 'wsb30_mae': 9.56},
      'notes': 'validation only',
      'validated': false,
    };

ModelManifest parse(Map<String, dynamic> m) => ModelManifest.parse(jsonEncode(m));

void expectInvalid(Map<String, dynamic> m, String reason) =>
    expect(() => parse(m), throwsA(isA<ManifestInvalid>()), reason: reason);

void main() {
  test('a complete manifest parses into typed fields', () {
    final m = parse(valid());
    expect([m.id, m.label, m.architecture, m.baseModel, m.licence], ['rfdetr-m', 'RF-DETR-M', 'RF-DETR',
        'Roboflow/rf-detr-medium', 'Apache-2.0']);
    expect([m.inputSize, m.threshold, m.reviewBelow, m.bytes, m.numClasses], [576, 0.48, 0.63, 121956743, 4]);
    expect(m.sha256, startsWith('07161f11'));
    expect([m.validation.countAccuracy, m.validation.speciesMap50, m.validation.wsb30Mae], [0.846, 0.933, 9.56]);
    expect([m.notes, m.validated], ['validation only', false]);
  });

  test('notes are optional; the manifest round-trips through JSON', () {
    final m = parse(valid()..remove('notes'));
    expect(m.notes, isNull);
    expect(ModelManifest.parse(jsonEncode(m.toJson())).toJson(), m.toJson());
  });

  test('integer-valued numbers are accepted where a number is expected', () {
    expect(parse(valid()..['validation'] = {'count_accuracy': 1, 'species_map50': 0.9, 'wsb30_mae': 9}).validation
        .wsb30Mae, 9.0);
  });

  test('not JSON, or not an object, is invalid', () {
    expect(() => ModelManifest.parse('{nope'), throwsA(isA<ManifestInvalid>()));
    expect(() => ModelManifest.parse('[1, 2]'), throwsA(isA<ManifestInvalid>()));
  });

  test('each missing required field is rejected', () {
    for (final k in valid().keys.where((k) => k != 'notes')) {
      expectInvalid(valid()..remove(k), 'missing $k');
    }
    for (final k in ['count_accuracy', 'species_map50', 'wsb30_mae']) {
      expectInvalid(valid()..['validation'] = ({...valid()['validation'] as Map}..remove(k)), 'missing validation.$k');
    }
  });

  test('unknown fields are rejected, at the top level and in validation', () {
    expectInvalid(valid()..['url'] = 'https://example.invalid', 'unknown top-level field');
    expectInvalid(valid()..['validation'] = {...valid()['validation'] as Map, 'map50_95': 0.5}, 'unknown validation field');
  });

  test('wrong types are rejected', () {
    final wrong = <String, Object?>{
      'id': 7, 'label': null, 'architecture': ['x'], 'base_model': 1, 'licence': true,
      'input_size': 576.5, 'threshold': '0.48', 'review_below': null, 'sha256': 1, 'bytes': 1.5,
      'outputs': 'logits', 'num_classes': '4', 'validation': [], 'notes': 3, 'validated': 'false',
    };
    for (final e in wrong.entries) {
      expectInvalid(valid()..[e.key] = e.value, '${e.key} = ${e.value}');
    }
  });

  test('input size must be 320 to 1280', () {
    expect(parse(valid()..['input_size'] = 320).inputSize, 320);
    expect(parse(valid()..['input_size'] = 1280).inputSize, 1280);
    expectInvalid(valid()..['input_size'] = 319, 'too small');
    expectInvalid(valid()..['input_size'] = 1281, 'too large');
  });

  test('thresholds must lie strictly between 0 and 1, and review_below not under the threshold', () {
    for (final v in [0, 1, -0.1, 1.2]) {
      expectInvalid(valid()..['threshold'] = v, 'threshold $v');
      expectInvalid(valid()..['review_below'] = v, 'review_below $v');
    }
    expectInvalid(valid()..['threshold'] = 0.6..['review_below'] = 0.5, 'review_below under the threshold');
    expect(parse(valid()..['threshold'] = 0.5..['review_below'] = 0.5).reviewBelow, 0.5);
  });

  test('the threshold must stay above the detector floor, or counts silently drop detections', () {
    expectInvalid(valid()..['threshold'] = 0.02, 'threshold at the floor');
  });

  test('the contract fields are fixed: outputs, four classes, a SHA-256, a positive size, a safe id', () {
    expectInvalid(valid()..['outputs'] = ['pred_boxes', 'logits'], 'outputs out of order');
    expectInvalid(valid()..['outputs'] = ['logits'], 'missing an output');
    expectInvalid(valid()..['num_classes'] = 80, 'num_classes');
    expectInvalid(valid()..['sha256'] = 'abc', 'short sha256');
    expectInvalid(valid()..['sha256'] = '07161F11D2BFC390510627DDFF72A8436045B1F79CCCD00682F19359FE5C660F', 'upper-case sha256');
    expectInvalid(valid()..['bytes'] = 0, 'zero bytes');
    for (final id in ['', '../evil', 'a/b', 'Upper', '.hidden', 'x' * 65]) {
      expectInvalid(valid()..['id'] = id, 'id "$id"');
    }
    expectInvalid(valid()..['label'] = '', 'empty label');
  });

  test('validation figures must be in range', () {
    Map<String, dynamic> v(String k, num x) => valid()..['validation'] = {...valid()['validation'] as Map, k: x};
    expectInvalid(v('count_accuracy', 1.1), 'accuracy above 1');
    expectInvalid(v('species_map50', -0.1), 'mAP below 0');
    expectInvalid(v('wsb30_mae', -1), 'negative MAE');
  });
}
