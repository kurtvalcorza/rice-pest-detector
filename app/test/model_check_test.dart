// The session check an imported model must pass before it is enabled: the ONNX session opens, its
// input and output names and shapes match the contract at the manifest's input size, and a synthetic
// photo produces outputs of the right length with finite values. ONNX Runtime is faked here.
import 'dart:typed_data';

import 'package:flutter_test/flutter_test.dart';
import 'package:rice_pest_app/inference/model_check.dart';
import 'package:rice_pest_app/model/model_manifest.dart';
import 'package:rice_pest_app/model/model_registry.dart';

ModelManifest manifest({int inputSize = 576}) => ModelManifest.fromJson({
      'id': 'rfdetr-m', 'label': 'RF-DETR-M', 'architecture': 'RF-DETR', 'base_model': 'x', 'licence': 'Apache-2.0',
      'input_size': inputSize, 'threshold': 0.48, 'review_below': 0.63, 'sha256': 'a' * 64, 'bytes': 1,
      'outputs': ['logits', 'pred_boxes'], 'num_classes': 4,
      'validation': {'count_accuracy': 0.846, 'species_map50': 0.933, 'wsb30_mae': 9.56}, 'validated': false,
    });

class FakeSession implements ProbeSession {
  FakeSession({List<TensorSpec>? inputs, List<TensorSpec>? outputs, this.result})
      : inputs = inputs ?? [const TensorSpec('pixel_values', [1, 3, 576, 576])],
        outputs = outputs ?? [const TensorSpec('logits', [1, 300, 4]), const TensorSpec('pred_boxes', [1, 300, 4])];
  @override
  final List<TensorSpec> inputs;
  @override
  final List<TensorSpec> outputs;
  final Map<String, List<double>>? result;
  List<int>? ranWith;
  bool closed = false;

  @override
  Future<Map<String, List<double>>> run(Float32List input, List<int> shape) async {
    ranWith = shape;
    expect(input.length, shape.reduce((a, b) => a * b));
    return result ?? {'logits': List.filled(1200, -3.0), 'pred_boxes': List.filled(1200, 0.5)};
  }

  @override
  Future<void> close() async => closed = true;
}

class FakeProbe implements ModelProbe {
  FakeProbe(this.session);
  final FakeSession session;
  @override
  Future<ProbeSession> open(String path) async => session;
}

FakeSession session({List<TensorSpec>? inputs, List<TensorSpec>? outputs, Map<String, List<double>>? result}) =>
    FakeSession(inputs: inputs, outputs: outputs, result: result);

Matcher fails(ImportFailure reason) =>
    throwsA(isA<ModelImportFailed>().having((e) => e.reason, 'reason', reason));

void main() {
  test('a model matching its manifest passes, runs once at its own input size, and is closed', () async {
    final s = session();
    await checkModel(FakeProbe(s), 'm.onnx', manifest());
    expect(s.ranWith, [1, 3, 576, 576]);
    expect(s.closed, isTrue);
  });

  test('a dynamic batch dimension is accepted', () async {
    await checkModel(FakeProbe(session(inputs: [const TensorSpec('pixel_values', [-1, 3, 576, 576])],
        outputs: [const TensorSpec('logits', [-1, 300, 4]), const TensorSpec('pred_boxes', [-1, 300, 4])])),
        'm.onnx', manifest());
  });

  test('an input size that differs from the manifest is a shape mismatch', () async {
    final s = session();
    await expectLater(checkModel(FakeProbe(s), 'm.onnx', manifest(inputSize: 640)), fails(ImportFailure.shapeMismatch));
    expect(s.closed, isTrue);
  });

  test('wrong input or output names or shapes are shape mismatches', () async {
    final bad = <FakeSession>[
      session(inputs: [const TensorSpec('images', [1, 3, 576, 576])]),
      session(inputs: [const TensorSpec('pixel_values', [1, 3, 576, 576]), const TensorSpec('mask', [1])]),
      session(outputs: [const TensorSpec('logits', [1, 300, 80]), const TensorSpec('pred_boxes', [1, 300, 4])]),
      session(outputs: [const TensorSpec('scores', [1, 300, 4]), const TensorSpec('pred_boxes', [1, 300, 4])]),
      session(outputs: [const TensorSpec('logits', [1, 100, 4]), const TensorSpec('pred_boxes', [1, 100, 4])]),
    ];
    for (final s in bad) {
      await expectLater(checkModel(FakeProbe(s), 'm.onnx', manifest()), fails(ImportFailure.shapeMismatch));
    }
  });

  test('outputs of the wrong length or with non-finite values fail the self-test', () async {
    for (final result in [
      {'logits': List.filled(1199, 0.0), 'pred_boxes': List.filled(1200, 0.5)},
      {'logits': List.filled(1200, 0.0)},
      {'logits': [...List.filled(1199, 0.0), double.nan], 'pred_boxes': List.filled(1200, 0.5)},
      {'logits': List.filled(1200, 0.0), 'pred_boxes': [double.infinity, ...List.filled(1199, 0.5)]},
    ]) {
      final s = session(result: result);
      await expectLater(checkModel(FakeProbe(s), 'm.onnx', manifest()), fails(ImportFailure.selfTestFailed));
      expect(s.closed, isTrue);
    }
  });

  test('a session that will not open fails the self-test', () async {
    await expectLater(checkModel(_Unopenable(), 'm.onnx', manifest()), fails(ImportFailure.selfTestFailed));
  });
}

class _Unopenable implements ModelProbe {
  @override
  Future<ProbeSession> open(String path) async => throw StateError('not an ONNX file');
}
