// The check an imported model must pass before it is enabled: the ONNX session opens, its input and
// output names and shapes match the inference contract at the manifest's input size, and a synthetic
// photo runs through it with outputs of the expected length and only finite values.
// ONNX Runtime sits behind ModelProbe so the rules are tested on the host.
import 'dart:typed_data';

import '../model/model_manifest.dart';
import '../model/model_registry.dart';
import 'contract.dart';
import 'preprocess.dart';

class TensorSpec {
  const TensorSpec(this.name, this.shape);
  final String name;

  /// -1 (or another negative value) marks a dynamic dimension.
  final List<int> shape;
}

abstract class ProbeSession {
  List<TensorSpec> get inputs;
  List<TensorSpec> get outputs;

  /// Runs [input] (NCHW, [shape]) and returns each output flattened.
  Future<Map<String, List<double>>> run(Float32List input, List<int> shape);
  Future<void> close();
}

abstract class ModelProbe {
  Future<ProbeSession> open(String path);
}

/// A deterministic test pattern (the same formula as the contract fixtures), so no photo is bundled.
RgbImage selfTestImage({int width = 64, int height = 48}) {
  final px = Uint8List(width * height * 3);
  for (var y = 0; y < height; y++) {
    for (var x = 0; x < width; x++) {
      for (var c = 0; c < 3; c++) {
        px[(y * width + x) * 3 + c] = (x * 7 + y * 13 + c * 101 + (x * y) % 31) % 256;
      }
    }
  }
  return RgbImage(width, height, px);
}

Future<void> checkModel(ModelProbe probe, String path, ModelManifest manifest) async {
  final ProbeSession session;
  try {
    session = await probe.open(path);
  } catch (e) {
    throw ModelImportFailed(ImportFailure.selfTestFailed, 'the ONNX session did not open: $e');
  }
  try {
    final size = manifest.inputSize;
    final input = [1, 3, size, size];
    final out = [1, numQueries, manifest.numClasses];
    final boxes = [1, numQueries, 4];
    _expectSpecs('input', session.inputs, {inputName: input});
    _expectSpecs('output', session.outputs, {logitsName: out, boxesName: boxes});

    final Map<String, List<double>> result;
    try {
      result = await session.run(preprocess(selfTestImage(), size: size), input);
    } catch (e) {
      throw ModelImportFailed(ImportFailure.selfTestFailed, 'the self-test run failed: $e');
    }
    for (final (name, shape) in [(logitsName, out), (boxesName, boxes)]) {
      final values = result[name];
      final want = shape.reduce((a, b) => a * b);
      if (values == null || values.length != want) {
        throw ModelImportFailed(ImportFailure.selfTestFailed, '$name has ${values?.length} values, expected $want');
      }
      if (values.any((v) => !v.isFinite)) {
        throw ModelImportFailed(ImportFailure.selfTestFailed, '$name has non-finite values');
      }
    }
  } finally {
    await session.close();
  }
}

void _expectSpecs(String kind, List<TensorSpec> got, Map<String, List<int>> want) {
  final names = got.map((t) => t.name).toSet();
  if (got.length != want.length || !names.containsAll(want.keys)) {
    throw ModelImportFailed(ImportFailure.shapeMismatch,
        '$kind names are ${names.join(', ')}; expected ${want.keys.join(', ')}');
  }
  for (final t in got) {
    final w = want[t.name]!;
    final ok = t.shape.length == w.length &&
        [for (var i = 0; i < w.length; i++) t.shape[i] == w[i] || (i == 0 && t.shape[i] < 0)].every((b) => b);
    if (!ok) throw ModelImportFailed(ImportFailure.shapeMismatch, '${t.name} has shape ${t.shape}; expected $w');
  }
}
