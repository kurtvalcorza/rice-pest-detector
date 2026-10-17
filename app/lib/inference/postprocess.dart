// Post-processing that reproduces rice_pest_detector.infer.postprocess.
import 'dart:math' as math;
import 'dart:typed_data';

import 'contract.dart';

class Detection {
  const Detection(this.classId, this.score, this.x0, this.y0, this.x1, this.y1);
  final int classId;
  final double score;
  final double x0, y0, x1, y1;
  String get species => speciesOfClass[classId]!;
}

/// [logits] and [boxes] are the flattened (1, 300, 4) outputs; boxes are normalised cx, cy, w, h.
/// [width] and [height] are the image size AFTER EXIF orientation. Score = max sigmoid over
/// classes; kept when score >= [threshold]; sorted by score, ties in query order; no NMS.
List<Detection> postprocess(Float32List logits, Float32List boxes, int width, int height,
    {double threshold = defaultThreshold}) {
  final nClasses = classNames.length;
  final queries = logits.length ~/ nClasses;
  final kept = <(int, Detection)>[];
  for (var q = 0; q < queries; q++) {
    var best = -1.0, cls = 0;
    for (var c = 0; c < nClasses; c++) {
      final p = 1.0 / (1.0 + math.exp(-logits[q * nClasses + c]));
      if (p > best) {
        best = p;
        cls = c;
      }
    }
    if (best >= threshold) {
      final cx = boxes[q * 4], cy = boxes[q * 4 + 1], w = boxes[q * 4 + 2], h = boxes[q * 4 + 3];
      kept.add((q, Detection(cls, best, (cx - w / 2) * width, (cy - h / 2) * height,
          (cx + w / 2) * width, (cy + h / 2) * height)));
    }
  }
  kept.sort((a, b) {
    final byScore = b.$2.score.compareTo(a.$2.score);
    return byScore != 0 ? byScore : a.$1.compareTo(b.$1);
  });
  return [for (final k in kept) k.$2];
}
