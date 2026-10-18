// The home-screen download pin (assets/model_pin.json) must point at the same file as the catalogue's
// default model, so the two download paths cannot drift apart.
import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:rice_pest_app/model/model_registry.dart';
import 'package:rice_pest_app/model/model_store.dart';
import 'package:rice_pest_app/model/published_models.dart';

String sep = Platform.pathSeparator;

void main() {
  test('the pin matches the catalogue entry of the default model', () {
    final pin = ModelPin.fromJson(File('assets${sep}model_pin.json').readAsStringSync());
    final models = parsePublishedModels(File('assets${sep}model_catalog.json').readAsStringSync());
    final entry = models.singleWhere((m) => m.manifest.sha256 == defaultModelSha256);

    expect(pin.sha256, defaultModelSha256);
    expect(pin.url, entry.url);
    expect(pin.bytes, entry.manifest.bytes);
    expect(pin.threshold, entry.manifest.threshold);
    expect(pin.label, entry.manifest.label);
    expect(pin.kind, 'demo');
  });
}
