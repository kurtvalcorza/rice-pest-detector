// The real ModelCatalog (registry + the legacy pin and demo.json) and the on-phone file picker.
// Models are imported from files the user picks on the phone, or downloaded from a URL in the bundled
// catalogue when the user taps Download; never from a URL the user types.
import 'dart:io';

import 'package:file_selector/file_selector.dart';
import 'package:http/http.dart' as http;

import '../inference/detector.dart';
import '../model/model_registry.dart';
import '../model/model_store.dart';
import '../model/published_models.dart';
import 'bootstrap.dart';
import 'services.dart';

class LocalModelCatalog implements ModelCatalog {
  LocalModelCatalog({required this.registry, required this.pin, required this.store, required this.demoStore,
      required this.demoMeta, required this.load, required this.check, required this.unload,
      this.published = const [], this.client});

  @override
  final List<PublishedModel> published;

  /// Injected in tests; a fresh client per download otherwise.
  final http.Client? client;

  final ModelRegistry registry;
  final ModelPin pin;
  final ModelStore store;
  final ModelStore demoStore;
  final File demoMeta;
  final DetectorLoader load;
  final ModelCheck check;
  final Future<void> Function(Detector) unload;

  @override
  Future<List<InstalledModel>> list() =>
      installedModels(pin: pin, store: store, demoStore: demoStore, demoMeta: demoMeta, registry: registry);

  @override
  Future<void> activate(String? id) => registry.setActive(id);

  @override
  Future<void> delete(String id) => registry.delete(id);

  @override
  Future<InstalledModel> importFrom({required File model, required File manifest}) =>
      registry.importModel(model: model, manifest: manifest, check: check);

  @override
  Future<InstalledModel> download(PublishedModel model,
      {void Function(int received, int? total)? onProgress, DownloadCancel? cancel}) async {
    final m = model.manifest;
    if (await registry.has(m.id)) throw ModelImportFailed(ImportFailure.alreadyInstalled, m.id);
    final part = registry.downloadPart(m.id);
    final client = this.client ?? http.Client();
    try {
      try {
        await fetchToFile(client, Uri.parse(model.url), part,
            onProgress: onProgress, cancel: cancel, maxBytes: m.bytes);
      } on ModelVerificationFailed catch (e) {
        throw ModelImportFailed(ImportFailure.sizeMismatch, e.detail);
      }
      // The registry verifies size and SHA-256 against the catalogue manifest, then runs the session check.
      return await registry.installDownloaded(part: part, manifest: m, check: check);
    } finally {
      if (this.client == null) client.close();
      if (await part.exists()) await part.delete();
    }
  }

  @override
  Future<Detector> open(InstalledModel model) => load(model);

  @override
  Future<void> close(Detector detector) => unload(detector);
}

/// The system file picker (Storage Access Framework on Android). The picked file is a local copy.
class FileSelectorModelFiles implements ModelFilePicker {
  @override
  Future<File?> pickManifest() => _pick();
  @override
  Future<File?> pickModel() => _pick();

  // No type filter: Android has no MIME type for .onnx, and the registry checks the contents anyway.
  Future<File?> _pick() async {
    final picked = await openFile();
    return picked == null ? null : File(picked.path);
  }
}
