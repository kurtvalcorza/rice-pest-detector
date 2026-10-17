// The published models the app can download (assets/model_catalog.json, bundled with the app). Each entry
// wraps a download URL around an unchanged model manifest, which is parsed by the same strict parser as a
// manifest.json file. URLs come only from this bundled file, never from the user.
import 'dart:convert';

import 'model_manifest.dart';

class PublishedModel {
  const PublishedModel({required this.url, required this.manifest});

  /// An https link to the .onnx file; the file must match [manifest]'s size and SHA-256.
  final String url;
  final ModelManifest manifest;
}

/// Parses the catalogue `{"models": [{"url": ..., "manifest": {...}}, ...]}`; throws [ManifestInvalid].
List<PublishedModel> parsePublishedModels(String source) {
  final Object? json;
  try {
    json = jsonDecode(source);
  } on FormatException catch (e) {
    throw ManifestInvalid('catalogue is not JSON (${e.message})');
  }
  if (json is! Map<String, dynamic> || json.keys.length != 1 || json['models'] is! List) {
    throw ManifestInvalid('catalogue must be {"models": [...]}');
  }
  final found = <PublishedModel>[];
  for (final e in json['models'] as List) {
    if (e is! Map<String, dynamic>) throw ManifestInvalid('catalogue entry is not an object');
    final keys = e.keys.toSet();
    if (keys.length != 2 || !keys.containsAll(const {'url', 'manifest'})) {
      throw ManifestInvalid('catalogue entry must have exactly "url" and "manifest"');
    }
    final url = e['url'];
    final uri = url is String ? Uri.tryParse(url) : null;
    if (uri == null || uri.scheme != 'https' || uri.host.isEmpty) {
      throw ManifestInvalid('catalogue url must be an https link');
    }
    final manifest = ModelManifest.fromJson(e['manifest']);
    if (found.any((p) => p.manifest.id == manifest.id)) throw ManifestInvalid('catalogue repeats ${manifest.id}');
    found.add(PublishedModel(url: url as String, manifest: manifest));
  }
  return found;
}
