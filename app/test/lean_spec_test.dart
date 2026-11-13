// The Dart post-processing against the Lean specification in formal/.
// Fixtures come from `lake exe fixtures` in formal/ (formal/Fixtures.lean); tests/test_lean_spec.py
// checks the Python reference against the same file.
import 'dart:convert';
import 'dart:io';
import 'dart:math' as math;
import 'dart:typed_data';

import 'package:flutter_test/flutter_test.dart';
import 'package:rice_pest_app/inference/postprocess.dart';

void main() {
  final spec = jsonDecode(File('test/fixtures/lean_spec_fixtures.json').readAsStringSync())
      as Map<String, dynamic>;

  test('postprocess matches the Lean specification', () {
    var checked = 0;
    for (final c in (spec['postprocess'] as List).cast<Map<String, dynamic>>()) {
      final rows = (c['logits_eighths'] as List).cast<List<dynamic>>();
      final n = rows.length;
      final logits = Float32List.fromList(
          [for (final row in rows) for (final v in row) (v as int) / 8]);
      // cx encodes the query index; sizes are zero.
      final boxes = Float32List.fromList([
        for (var q = 0; q < n; q++) ...[(q + 0.5) / n, 0.0, 0.0, 0.0],
      ]);
      for (final r in (c['results'] as List).cast<Map<String, dynamic>>()) {
        final t = (r['threshold_eighths'] as int) / 8;
        final got = postprocess(logits, boxes, n, 100, threshold: 1.0 / (1.0 + math.exp(-t)));
        final ids = [
          for (final d in got) [((d.x0 + d.x1) / 2 - 0.5).round(), d.classId],
        ];
        expect(ids, r['expected'], reason: 'seed ${c['seed']}, threshold ${r['threshold_eighths']}');
        checked += got.length;
      }
    }
    expect(checked, greaterThan(500));
  });
}
