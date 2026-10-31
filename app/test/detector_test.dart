import 'dart:async';
import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';
import 'package:rice_pest_app/inference/detector.dart';

// Fixture shape: recorded ONNX outputs per image.
final fixtures = jsonEncode({
  'onnx_sha256': 'abc123',
  'threshold': 0.5,
  'images': [
    {
      'file': 'tray-1.jpg', 'width': 640, 'height': 640,
      'detections': [
        {'class_id': 2, 'score': 0.5, 'box': [10, 20, 30, 40], 'constructed': true},
        {'class_id': 0, 'score': 0.91, 'box': [1, 2, 3, 4], 'constructed': false},
      ],
    },
  ],
});

void main() {
  test('FakeDetector replays recorded detections sorted by score', () async {
    final det = FakeDetector.fromJson(fixtures);
    final got = await det.detect(PhotoRef('tray-1.jpg'));
    expect(got.map((g) => g.classId), [0, 2]);
    expect(got.map((g) => g.species), ['RBB', 'WSB']);
    expect(got.last.score, 0.5);
    expect([got.last.x0, got.last.y0, got.last.x1, got.last.y1], [10, 20, 30, 40]);
    expect(det.modelId, 'fake:abc123');
  });

  test('FakeDetector refuses a photo it has no recording for', () async {
    final det = FakeDetector.fromJson(fixtures);
    expect(() => det.detect(PhotoRef('missing.jpg')), throwsA(isA<StateError>()));
  });

  test('TrackedDetector is idle only once every running count has finished', () async {
    final gate = Completer<void>();
    final tracked = TrackedDetector(_Gated(gate.future));
    await tracked.idle(); // nothing running: completes at once
    final counting = tracked.detect(const PhotoRef('trap-1.jpg'));
    var idle = false;
    unawaited(tracked.idle().then((_) => idle = true));
    await Future<void>.delayed(Duration.zero);
    expect(idle, isFalse, reason: 'a count is still running');
    gate.complete();
    await counting;
    await Future<void>.delayed(Duration.zero);
    expect(idle, isTrue);
    expect(tracked.modelId, 'gated');
  });
}

class _Gated implements Detector {
  _Gated(this.gate);
  final Future<void> gate;
  @override
  String get modelId => 'gated';
  @override
  Future<List<Never>> detect(PhotoRef photo) async {
    await gate;
    return const [];
  }
}
