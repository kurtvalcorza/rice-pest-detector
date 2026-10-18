// A model manifest: one JSON file next to each .onnx, describing the model and how the app counts with
// it. Parsing is strict (unknown, missing or out-of-range fields are rejected), because an imported
// model is enabled only when everything about it checks out.
import 'dart:convert';

import '../inference/contract.dart';

class ManifestInvalid implements Exception {
  ManifestInvalid(this.detail);
  final String detail;
  @override
  String toString() => 'Model manifest is not valid: $detail';
}

/// Validation count accuracy of a model that always answers "no insects", on the same validation photos
/// (docs/evaluation-record.md: 0.4743). Every count accuracy the app shows is shown beside it.
const double doNothingCountAccuracy = 0.474;

class ModelValidation {
  const ModelValidation({required this.countAccuracy, required this.speciesMap50, required this.wsb30Mae});

  /// Out-of-fold validation count accuracy.
  final double countAccuracy;
  final double speciesMap50;

  /// White stemborer count error on the dense (30 or more) validation trays.
  final double wsb30Mae;

  Map<String, dynamic> toJson() =>
      {'count_accuracy': countAccuracy, 'species_map50': speciesMap50, 'wsb30_mae': wsb30Mae};
}

class ModelManifest {
  const ModelManifest({required this.id, required this.label, required this.architecture,
      required this.baseModel, required this.licence, required this.inputSize, required this.threshold,
      required this.reviewBelow, required this.sha256, required this.bytes, required this.numClasses,
      required this.validation, required this.validated, this.notes});

  static const minInputSize = 320;
  static const maxInputSize = 1280;
  static const _required = {
    'id', 'label', 'architecture', 'base_model', 'licence', 'input_size', 'threshold', 'review_below',
    'sha256', 'bytes', 'outputs', 'num_classes', 'validation', 'validated',
  };
  static const _optional = {'notes'};
  static const _validationKeys = {'count_accuracy', 'species_map50', 'wsb30_mae'};
  static final _id = RegExp(r'^[a-z0-9][a-z0-9._-]{0,63}$');
  static final _sha = RegExp(r'^[0-9a-f]{64}$');

  factory ModelManifest.parse(String source) {
    final Object? json;
    try {
      json = jsonDecode(source);
    } on FormatException catch (e) {
      throw ManifestInvalid('not JSON (${e.message})');
    }
    return ModelManifest.fromJson(json);
  }

  factory ModelManifest.fromJson(Object? json) {
    if (json is! Map<String, dynamic>) throw ManifestInvalid('not a JSON object');
    _exactKeys(json, _required, _optional, 'manifest');

    final id = _string(json, 'id');
    if (!_id.hasMatch(id)) throw ManifestInvalid('id must be 1-64 lower-case letters, digits, ".", "_" or "-"');
    final label = _string(json, 'label');
    if (label.trim().isEmpty) throw ManifestInvalid('label is empty');

    final inputSize = json['input_size'];
    if (inputSize is! int) throw ManifestInvalid('input_size must be an integer');
    if (inputSize < minInputSize || inputSize > maxInputSize) {
      throw ManifestInvalid('input_size must be $minInputSize to $maxInputSize');
    }

    final threshold = _number(json, 'threshold');
    final reviewBelow = _number(json, 'review_below');
    for (final (name, v) in [('threshold', threshold), ('review_below', reviewBelow)]) {
      if (!(v > 0 && v < 1)) throw ManifestInvalid('$name must lie strictly between 0 and 1');
    }
    if (threshold <= detectorFloor) throw ManifestInvalid('threshold must be above the detector floor $detectorFloor');
    if (reviewBelow < threshold) throw ManifestInvalid('review_below must not be under the threshold');

    final sha = _string(json, 'sha256');
    if (!_sha.hasMatch(sha)) throw ManifestInvalid('sha256 must be 64 lower-case hex digits');
    final bytes = json['bytes'];
    if (bytes is! int || bytes <= 0) throw ManifestInvalid('bytes must be a positive integer');

    final outputs = json['outputs'];
    if (outputs is! List || outputs.length != 2 || outputs[0] != logitsName || outputs[1] != boxesName) {
      throw ManifestInvalid('outputs must be ["$logitsName", "$boxesName"]');
    }
    final numClasses = json['num_classes'];
    if (numClasses is! int || numClasses != classNames.length) {
      throw ManifestInvalid('num_classes must be ${classNames.length}');
    }

    final v = json['validation'];
    if (v is! Map<String, dynamic>) throw ManifestInvalid('validation must be an object');
    _exactKeys(v, _validationKeys, const {}, 'validation');
    final validation = ModelValidation(countAccuracy: _number(v, 'count_accuracy'),
        speciesMap50: _number(v, 'species_map50'), wsb30Mae: _number(v, 'wsb30_mae'));
    final fractions = [('count_accuracy', validation.countAccuracy), ('species_map50', validation.speciesMap50)];
    for (final (name, x) in fractions) {
      if (x < 0 || x > 1) throw ManifestInvalid('validation.$name must be 0 to 1');
    }
    if (validation.wsb30Mae < 0) throw ManifestInvalid('validation.wsb30_mae must not be negative');

    final validated = json['validated'];
    if (validated is! bool) throw ManifestInvalid('validated must be true or false');
    final notes = json['notes'];
    if (notes != null && notes is! String) throw ManifestInvalid('notes must be a string');

    return ModelManifest(id: id, label: label, architecture: _string(json, 'architecture'),
        baseModel: _string(json, 'base_model'), licence: _string(json, 'licence'), inputSize: inputSize,
        threshold: threshold, reviewBelow: reviewBelow, sha256: sha, bytes: bytes, numClasses: numClasses,
        validation: validation, validated: validated, notes: notes as String?);
  }

  final String id;
  final String label;
  final String architecture;
  final String baseModel;
  final String licence;

  /// Square input side in pixels; preprocessing resizes every photo to this.
  final int inputSize;

  /// Detections scoring at or above this are counted.
  final double threshold;

  /// A counted detection scoring below this flags the photo for review.
  final double reviewBelow;
  final String sha256;
  final int bytes;
  final int numClasses;
  final ModelValidation validation;

  /// False for a model that has validation results only (not field-validated, not release-gated).
  final bool validated;
  final String? notes;

  Map<String, dynamic> toJson() => {
        'id': id, 'label': label, 'architecture': architecture, 'base_model': baseModel, 'licence': licence,
        'input_size': inputSize, 'threshold': threshold, 'review_below': reviewBelow, 'sha256': sha256,
        'bytes': bytes, 'outputs': [logitsName, boxesName], 'num_classes': numClasses,
        'validation': validation.toJson(), if (notes != null) 'notes': notes, 'validated': validated,
      };

  static void _exactKeys(Map<String, dynamic> m, Set<String> required, Set<String> optional, String where) {
    final missing = required.difference(m.keys.toSet());
    if (missing.isNotEmpty) throw ManifestInvalid('$where is missing ${missing.join(', ')}');
    final unknown = m.keys.toSet().difference({...required, ...optional});
    if (unknown.isNotEmpty) throw ManifestInvalid('$where has unknown field ${unknown.join(', ')}');
  }

  static String _string(Map<String, dynamic> m, String k) {
    final v = m[k];
    if (v is! String) throw ManifestInvalid('$k must be a string');
    return v;
  }

  static double _number(Map<String, dynamic> m, String k) {
    final v = m[k];
    if (v is! num) throw ManifestInvalid('$k must be a number');
    return v.toDouble();
  }
}
