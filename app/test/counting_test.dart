// Counting rules. The demonstration app has no alert
// (counts plus "share the counts", no treatment advice).
import 'package:flutter_test/flutter_test.dart';
import 'package:rice_pest_app/counting/counting.dart';
import 'package:rice_pest_app/inference/postprocess.dart';

Detection d(String species, double score) =>
    Detection(species == 'RBB' ? 0 : 2, score, 0, 0, 1, 1);

void main() {
  test('batch mean counts photos without the species as zero', () {
    final photos = [
      countPhoto('a.jpg', List.filled(4, d('WSB', .9))),
      countPhoto('b.jpg', [d('RBB', .9)]),
      countPhoto('c.jpg', [d('RBB', .9)]),
      countPhoto('d.jpg', [d('RBB', .9)]),
    ];
    final s = summarize(photos);
    expect(s.meanPerPhoto['WSB'], 1.0); // 4 stemborers / 4 photos, not 4 / 1
    expect(s.meanPerPhoto['RBB'], 0.75);
    expect(s.photos, 4);
  });

  test('threshold is inclusive', () {
    final p = countPhoto('a.jpg', [d('RBB', 0.5), d('RBB', 0.4999)]);
    expect(p.counts['RBB'], 1);
    expect(p.counts['WSB'], 0);
  });

  test('review flags for low confidence and crowding', () {
    final low = countPhoto('a.jpg', [d('RBB', 0.5)], threshold: 0.48); // counted, but below 0.64
    final crowded = countPhoto('b.jpg', List.filled(31, d('RBB', 0.9)));
    expect(countPhoto('f.jpg', [d('RBB', 0.64)], threshold: 0.48).needsReview, isFalse); // 0.64 itself is fine
    final fine = countPhoto('c.jpg', [d('RBB', 0.9)]);
    expect(low.reasons, [ReviewReason.lowConfidence]);
    expect(crowded.reasons, [ReviewReason.crowded]);
    expect(fine.needsReview, isFalse);
    expect(countPhoto('e.jpg', List.filled(30, d('RBB', 0.9))).needsReview, isFalse); // > 30, not >= 30
  });

  test('an empty batch has zero means, not a division error', () {
    final s = summarize([]);
    expect(s.photos, 0);
    expect(s.meanPerPhoto, {'RBB': 0.0, 'WSB': 0.0});
  });

  test('counts record the threshold they were made at', () {
    expect(countPhoto('a.jpg', [], threshold: 0.45).threshold, 0.45);
  });

  test('each model brings its own threshold and review flag', () {
    // RF-DETR-M style: count at 0.48, flag below 0.63; D-FINE-L style: count at 0.50, flag below 0.68.
    final dets = [d('RBB', 0.49), d('WSB', 0.66)];
    final rf = countPhoto('a.jpg', dets, threshold: 0.48, reviewBelow: 0.63);
    expect([rf.counts['RBB'], rf.counts['WSB'], rf.reasons], [1, 1, [ReviewReason.lowConfidence]]);
    final df = countPhoto('a.jpg', dets, threshold: 0.50, reviewBelow: 0.68);
    expect([df.counts['RBB'], df.counts['WSB'], df.reasons], [0, 1, [ReviewReason.lowConfidence]]);
    final high = countPhoto('a.jpg', [d('WSB', 0.66)], threshold: 0.48, reviewBelow: 0.63);
    expect(high.needsReview, isFalse);
  });

  test('the default review flag is r50-v5 value 0.64 and crowding stays at more than 30', () {
    expect(defaultReviewBelow, 0.64);
    expect(crowdedAbove, 30);
    expect(countPhoto('a.jpg', List.filled(31, d('RBB', 0.9)), threshold: 0.5, reviewBelow: 0.95).reasons,
        [ReviewReason.lowConfidence, ReviewReason.crowded]);
  });
}
