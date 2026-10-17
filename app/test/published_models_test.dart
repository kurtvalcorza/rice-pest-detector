// The bundled catalogue of published models (assets/model_catalog.json): each entry is a download URL
// plus a manifest, and the manifests must stay identical to the ones in ../models so they cannot drift.
import 'dart:convert';
import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:rice_pest_app/model/model_manifest.dart';
import 'package:rice_pest_app/model/model_registry.dart';
import 'package:rice_pest_app/model/published_models.dart';

String sep = Platform.pathSeparator;

Map<String, dynamic> catalogueJson() =>
    jsonDecode(File('assets${sep}model_catalog.json').readAsStringSync()) as Map<String, dynamic>;

void main() {
  test('the bundled catalogue lists the three published models with https download URLs', () {
    final models = parsePublishedModels(File('assets${sep}model_catalog.json').readAsStringSync());
    expect(models.map((m) => m.manifest.id), ['r50-v5', 'rfdetr-m', 'dfine-l']);
    for (final m in models) {
      expect(Uri.parse(m.url).scheme, 'https');
      expect(m.url, endsWith('/model.onnx'));
    }
    expect(models.first.manifest.sha256, defaultModelSha256, reason: 'r50-v5 is the default model');
  });

  test('each catalogue manifest equals the manifest file in ../models', () {
    final files = Directory('..${sep}models')
        .listSync()
        .whereType<File>()
        .where((f) => f.path.endsWith('.manifest.json'))
        .map((f) => jsonDecode(f.readAsStringSync()) as Map<String, dynamic>)
        .toList();
    expect(files, hasLength(3));
    final entries = [for (final e in catalogueJson()['models'] as List) (e as Map<String, dynamic>)['manifest']];
    expect(entries, hasLength(files.length));
    for (final file in files) {
      final entry = entries.singleWhere((e) => (e as Map)['id'] == file['id'], orElse: () => null);
      expect(entry, file, reason: file['id'] as String);
    }
  });

  Map<String, dynamic> entry({String url = 'https://example.invalid/model.onnx', Map<String, dynamic>? manifest}) =>
      {'url': url, 'manifest': manifest ?? (catalogueJson()['models'] as List).first['manifest']};

  String catalogue(List<Object?> entries, {Map<String, dynamic> extra = const {}}) =>
      jsonEncode({'models': entries, ...extra});

  test('a valid entry parses with its manifest unchanged', () {
    final m = parsePublishedModels(catalogue([entry()])).single;
    expect(m.url, 'https://example.invalid/model.onnx');
    expect(m.manifest.toJson(), ModelManifest.fromJson(entry()['manifest']).toJson());
  });

  test('the parser rejects what it does not expect', () {
    final good = entry();
    final bad = <String, String>{
      'not JSON': '{oops',
      'not an object': '[]',
      'unknown top-level field': catalogue([good], extra: {'extra': 1}),
      'models not a list': jsonEncode({'models': {}}),
      'entry not an object': catalogue([1]),
      'missing url': catalogue([{'manifest': good['manifest']}]),
      'unknown entry field': catalogue([{...good, 'mirror': 'x'}]),
      'http, not https': catalogue([entry(url: 'http://example.invalid/model.onnx')]),
      'not a URL': catalogue([entry(url: 'model.onnx')]),
      'invalid manifest': catalogue([entry(manifest: {'id': 'x'})]),
      'duplicate id': catalogue([good, entry(url: 'https://example.invalid/other.onnx')]),
    };
    for (final e in bad.entries) {
      expect(() => parsePublishedModels(e.value), throwsA(isA<ManifestInvalid>()), reason: e.key);
    }
  });
}
