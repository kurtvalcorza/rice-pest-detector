// Per-photo species counts and review flags. No alert: the app only shows counts, never advice.
import '../inference/contract.dart';
import '../inference/postprocess.dart';

// The low-confidence review flag comes from each model's manifest (review_below): the raw score whose
// calibrated probability of being a real insect is about 74% on validation photos. This default is the
// default model r50-v5's value (docs/evaluation-record.md, "Wave 2"), used for models without a manifest.
const double defaultReviewBelow = 0.64;
const int crowdedAbove = 30;
const List<String> speciesCodes = ['RBB', 'WSB'];

enum ReviewReason { lowConfidence, crowded }

class PhotoCount {
  PhotoCount(this.photo, this.counts, this.reasons, this.threshold);
  final String photo;
  final Map<String, int> counts;
  final List<ReviewReason> reasons;
  final double threshold;
  bool get needsReview => reasons.isNotEmpty;
}

/// Count detections scoring >= [threshold] (inclusive). Flag the photo for review when any counted
/// detection scores below [reviewBelow], or when more than [crowdedAbove] are counted. Both thresholds
/// are per model; crowding is not.
PhotoCount countPhoto(String photo, List<Detection> detections,
    {double threshold = defaultThreshold, double reviewBelow = defaultReviewBelow}) {
  final kept = [for (final d in detections) if (d.score >= threshold) d];
  final counts = {for (final s in speciesCodes) s: kept.where((d) => d.species == s).length};
  final reasons = <ReviewReason>[
    if (kept.any((d) => d.score < reviewBelow)) ReviewReason.lowConfidence,
    if (kept.length > crowdedAbove) ReviewReason.crowded,
  ];
  return PhotoCount(photo, counts, reasons, threshold);
}

class BatchSummary {
  BatchSummary(this.photos, this.meanPerPhoto);
  final int photos;
  final Map<String, double> meanPerPhoto;
}

/// Mean per photo over ALL photos: a photo without a species counts as zero for it.
BatchSummary summarize(List<PhotoCount> photos) {
  final n = photos.isEmpty ? 1 : photos.length;
  return BatchSummary(photos.length, {
    for (final s in speciesCodes) s: photos.fold<int>(0, (sum, p) => sum + p.counts[s]!) / n,
  });
}
