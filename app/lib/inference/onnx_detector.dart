// Real-model detector: ONNX Runtime on the device via flutter_onnxruntime (ONNX Runtime 1.28).
import 'dart:io';
import 'dart:typed_data';

import 'package:flutter_onnxruntime/flutter_onnxruntime.dart';

import 'contract.dart';
import 'contract.dart' as contract show inputSize;
import 'decode.dart';
import 'detector.dart';
import 'model_check.dart';
import 'postprocess.dart';
import 'preprocess.dart';

class OnnxDetector implements Detector {
  OnnxDetector._(this.modelId, this._session, this.inputSize);

  /// Detections below this are dropped before counting; counting applies the real threshold.
  /// Keep it below every counting threshold (demo thresholds so far: 0.04 for r50-1, 0.48 for r50-v5;
  /// manifests are rejected unless their threshold is above it).
  static const double minScore = detectorFloor;

  static Future<OnnxDetector> fromAsset(String assetKey,
          {required String modelId, int inputSize = contract.inputSize}) async =>
      OnnxDetector._(modelId, await OnnxRuntime().createSessionFromAsset(assetKey), inputSize);

  static Future<OnnxDetector> fromFile(String path,
          {required String modelId, int inputSize = contract.inputSize}) async =>
      OnnxDetector._(modelId, await OnnxRuntime().createSession(path), inputSize);

  @override
  final String modelId;
  final OrtSession _session;

  /// Square input side the model was exported at (its manifest's input_size; 640 by contract default).
  final int inputSize;

  @override
  Future<List<Detection>> detect(PhotoRef photo) async {
    final path = photo.path;
    if (path == null) throw ArgumentError('PhotoRef ${photo.name} has no file path');
    return detectUpright(decodePhoto(await File(path).readAsBytes()).image);
  }

  /// Run the contract on pixels that are already upright (EXIF orientation applied).
  Future<List<Detection>> detectUpright(RgbImage upright) async {
    final input = await OrtValue.fromList(preprocess(upright, size: inputSize), [1, 3, inputSize, inputSize]);
    try {
      final out = await _session.run({inputName: input});
      try {
        final logits = await _floats(out[logitsName]);
        final boxes = await _floats(out[boxesName]);
        return postprocess(logits, boxes, upright.width, upright.height, threshold: minScore);
      } finally {
        for (final v in out.values) {
          await v.dispose();
        }
      }
    } finally {
      await input.dispose();
    }
  }

  static Future<Float32List> _floats(OrtValue? v) async {
    if (v == null) throw StateError('model output missing: expected $logitsName and $boxesName');
    final flat = await v.asFlattenedList();
    if (flat.length != numQueries * 4) {
      throw StateError('model output has ${flat.length} values, expected ${numQueries * 4}');
    }
    return Float32List.fromList([for (final x in flat) (x as num).toDouble()]);
  }

  Future<void> close() => _session.close();
}

/// ONNX Runtime behind the import check (model_check.dart).
class OnnxProbe implements ModelProbe {
  @override
  Future<ProbeSession> open(String path) async {
    final session = _OnnxProbeSession(await OnnxRuntime().createSession(path));
    try {
      await session.load();
    } catch (_) {
      await session.close();
      rethrow;
    }
    return session;
  }
}

class _OnnxProbeSession implements ProbeSession {
  _OnnxProbeSession(this._session);
  final OrtSession _session;
  List<TensorSpec>? _inputs, _outputs;

  Future<void> load() async {
    _inputs = _specs(await _session.getInputInfo());
    _outputs = _specs(await _session.getOutputInfo());
  }

  static List<TensorSpec> _specs(List<Map<String, dynamic>> info) => [
        for (final i in info)
          TensorSpec(i['name'] as String, [for (final d in (i['shape'] as List? ?? const [])) (d as num).toInt()]),
      ];

  @override
  List<TensorSpec> get inputs => _inputs!;
  @override
  List<TensorSpec> get outputs => _outputs!;

  @override
  Future<Map<String, List<double>>> run(Float32List input, List<int> shape) async {
    final value = await OrtValue.fromList(input, shape);
    try {
      final out = await _session.run({inputName: value});
      try {
        return {
          for (final e in out.entries)
            e.key: [for (final x in await e.value.asFlattenedList()) (x as num).toDouble()],
        };
      } finally {
        for (final v in out.values) {
          await v.dispose();
        }
      }
    } finally {
      await value.dispose();
    }
  }

  @override
  Future<void> close() => _session.close();
}
