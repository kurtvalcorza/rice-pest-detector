import 'dart:convert';
import 'dart:io';

import 'package:crypto/crypto.dart';
import 'package:flutter_test/flutter_test.dart';

Map<String, dynamic> arb(String locale) =>
    jsonDecode(File('lib/l10n/app_$locale.arb').readAsStringSync()) as Map<String, dynamic>;

Set<String> keys(Map<String, dynamic> a) => a.keys.where((k) => !k.startsWith('@')).toSet();

Set<String> placeholders(String s) => RegExp(r'\{(\w+)\}').allMatches(s).map((m) => m[1]!).toSet();

/// Owner decision 2026-10-15 and the model card: no treatment or spray advice anywhere.
const treatmentWords = [
  'spray', 'pesticide', 'insecticide', 'chemical', 'apply ', 'dose',
  'pestisidyo', 'insektisidyo', 'kemikal', 'mag-spray', 'i-spray', 'bombahin', 'gamot',
];

void main() {
  final en = arb('en'), fil = arb('fil');

  test('Filipino and English have the same keys', () {
    expect(keys(fil), keys(en));
  });

  test('placeholders match between languages', () {
    for (final k in keys(en)) {
      expect(placeholders(fil[k] as String), placeholders(en[k] as String), reason: k);
    }
  });

  test('no string gives treatment or spray advice', () {
    for (final a in [en, fil]) {
      for (final k in keys(a)) {
        final s = (a[k] as String).toLowerCase();
        for (final w in treatmentWords) {
          expect(s.contains(w), isFalse, reason: '"$k" contains "$w"');
        }
      }
    }
  });

  test('the referral and the experimental-model notice exist in both languages', () {
    for (final k in ['shareCounts', 'modelNotice', 'privacyNotice', 'demoNotice']) {
      expect(keys(en), contains(k));
    }
  });

  test('no string addresses farmers or a technician as the audience', () {
    // Owner decision 2026-10-18: a teaching demonstration, not made for farmers.
    const audienceWords = ['farmer', 'magsasaka', 'technician', 'tekniko'];
    for (final a in [en, fil]) {
      for (final k in keys(a)) {
        final s = (a[k] as String).toLowerCase();
        for (final w in audienceWords) {
          expect(s.contains(w), isFalse, reason: '"$k" contains "$w"');
        }
      }
    }
  });

  test('no string names an organisation', () {
    // Uppercase word tokens are hashed so the excluded names are not written here.
    const excluded = {
      'f1782bec7b77a42a37dd169e19530a3cc153882a54d30c841e6732466afcc2b4',
      '5baf790cb73606f69a625ea5af1849afc95bf8d90a869d582f8727469f88ef6c',
    };
    for (final a in [en, fil]) {
      for (final k in keys(a)) {
        final words = (a[k] as String).toUpperCase().split(RegExp('[^A-Z]+'));
        for (final w in words.where((w) => w.isNotEmpty)) {
          expect(excluded, isNot(contains(sha256.convert(utf8.encode(w)).toString())), reason: k);
        }
      }
    }
  });
}