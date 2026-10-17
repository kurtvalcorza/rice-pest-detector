// The detector drops low scores before counting. That floor must sit below every counting threshold
// the app uses, or detections between the floor and the threshold are silently never counted.
// Demo thresholds come from demo.json, chosen on validation photos: 0.04 for r50-1, the lowest so far,
// and 0.48 for r50-v5.
import 'package:flutter_test/flutter_test.dart';
import 'package:rice_pest_app/inference/onnx_detector.dart';

void main() {
  test('the detector floor is below the lowest demo threshold, 0.04', () {
    expect(OnnxDetector.minScore, lessThan(0.04));
  });
}
