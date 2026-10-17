// Detector interface. FakeDetector replays recorded outputs so the
// app can be built and tested before a model passes its gates; OnnxDetector runs the real model.
import 'dart:convert';

import 'postprocess.dart';

/// A photo to analyse. [name] keys FakeDetector recordings; [path] is the file on the device.
class PhotoRef {
  const PhotoRef(this.name, [this.path]);
  final String name;
  final String? path;
}

abstract class Detector {
  /// Identifies the model behind every count: shown on results and stored in history.
  String get modelId;

  /// All detections the model reports, unthresholded except for the model's own floor,
  /// sorted by score. Counting applies the threshold.
  Future<List<Detection>> detect(PhotoRef photo);
}

class FakeDetector implements Detector {
  FakeDetector._(this.modelId, this._byFile);

  factory FakeDetector.fromJson(String json) {
    final data = jsonDecode(json) as Map<String, dynamic>;
    final byFile = <String, List<Detection>>{};
    for (final img in (data['images'] as List).cast<Map<String, dynamic>>()) {
      final dets = [
        for (final d in (img['detections'] as List).cast<Map<String, dynamic>>())
          Detection(d['class_id'] as int, (d['score'] as num).toDouble(),
              (d['box'][0] as num).toDouble(), (d['box'][1] as num).toDouble(),
              (d['box'][2] as num).toDouble(), (d['box'][3] as num).toDouble()),
      ]..sort((a, b) => b.score.compareTo(a.score));
      byFile[img['file'] as String] = dets;
    }
    return FakeDetector._('fake:${data['onnx_sha256']}', byFile);
  }

  @override
  final String modelId;
  final Map<String, List<Detection>> _byFile;

  @override
  Future<List<Detection>> detect(PhotoRef photo) async {
    final dets = _byFile[photo.name];
    if (dets == null) throw StateError('No recorded detections for ${photo.name}');
    return dets;
  }
}
