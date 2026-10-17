// Installed models. Each model lives in its own folder in app storage, models/<id>/model.onnx plus
// manifest.json, and active.json names the model the user chose. An import (picked file) or a download
// (published model) is put in a staging folder, checked (size, SHA-256, then the caller's ONNX session
// check) and only then moved into place, so a failure leaves nothing behind and never changes the active
// model.
import 'dart:convert';
import 'dart:io';

import 'package:crypto/crypto.dart';

import 'model_manifest.dart';

/// The default model, r50-v5, is identified by its file's SHA-256 so that a manifest cannot claim the
/// default's id to escape the "not validated" banner.
const String defaultModelId = 'r50-v5';
const String defaultModelSha256 = 'dc3927ae0967f6553721e18eec826305cca66c7fb5c8cd1789a8187d74f069c1';

/// Where an installed model came from: imported into the registry, the pinned download, or a developer's
/// side-loaded demo/demo.json.
enum ModelSource { registry, pin, sideloaded }

class InstalledModel {
  const InstalledModel({required this.id, required this.label, required this.sha256, required this.inputSize,
      required this.threshold, required this.reviewBelow, required this.path, required this.source,
      this.architecture = '', this.validation, this.validated = false, this.published = false});

  final String id;

  /// Shown to the user and recorded as the model id with every count.
  final String label;
  final String architecture;
  final String sha256;
  final int inputSize;
  final double threshold;
  final double reviewBelow;

  /// The .onnx file on the device.
  final String path;
  final ModelSource source;

  /// Null for models without a manifest (the pin and demo.json).
  final ModelValidation? validation;
  final bool validated;

  /// A pinned model whose pin says "published" (passed the release gates).
  final bool published;

  bool get isDefault => sha256 == defaultModelSha256;

  /// Only imported models can be removed, and never the default.
  bool get deletable => source == ModelSource.registry && !isDefault;
}

enum ImportFailure { manifestInvalid, sizeMismatch, checksumMismatch, shapeMismatch, selfTestFailed, alreadyInstalled,
  unreadable }

class ModelImportFailed implements Exception {
  ModelImportFailed(this.reason, this.detail);
  final ImportFailure reason;
  final String detail;
  @override
  String toString() => 'Model import failed (${reason.name}): $detail';
}

/// Opens the staged model and checks it against its manifest; throws [ModelImportFailed] if it does not fit.
typedef ModelCheck = Future<void> Function(String modelPath, ModelManifest manifest);

/// The default model first, then by label.
List<InstalledModel> sortModels(Iterable<InstalledModel> models) => [...models]..sort((a, b) {
    if (a.isDefault != b.isDefault) return a.isDefault ? -1 : 1;
    return a.label.toLowerCase().compareTo(b.label.toLowerCase());
  });

class ModelRegistry {
  ModelRegistry(this.root);
  final Directory root;

  /// Largest manifest read; anything bigger is not a manifest.
  static const _maxManifestBytes = 64 * 1024;

  String get _sep => Platform.pathSeparator;
  Directory _dir(String id) => Directory('${root.path}$_sep$id');
  File _model(Directory d) => File('${d.path}${_sep}model.onnx');
  File _manifest(Directory d) => File('${d.path}${_sep}manifest.json');

  /// Written after the file's SHA-256 is verified, so start-up does not hash every model each time.
  File _stamp(Directory d) => File('${d.path}${_sep}verified.json');
  File get _active => File('${root.path}${_sep}active.json');

  Future<List<InstalledModel>> list() async {
    if (!await root.exists()) return [];
    final found = <InstalledModel>[];
    await for (final e in root.list()) {
      if (e is! Directory) continue;
      final name = e.uri.pathSegments.where((s) => s.isNotEmpty).last;
      if (name.startsWith('.')) continue; // staging folders
      final m = await _read(e);
      if (m != null && m.id == name) found.add(m);
    }
    return sortModels(found);
  }

  Future<InstalledModel?> _read(Directory d) async {
    final ModelManifest manifest;
    try {
      final f = _manifest(d);
      if (!await f.exists() || await f.length() > _maxManifestBytes) return null;
      manifest = ModelManifest.parse(await f.readAsString());
    } on ManifestInvalid {
      return null;
    } on FileSystemException {
      return null;
    }
    final model = _model(d);
    if (!await model.exists() || await model.length() != manifest.bytes) return null;
    if (!await _stamped(d, manifest)) {
      if (await _sha256(model) != manifest.sha256) return null;
      await _writeStamp(d, manifest, await model.lastModified());
    }
    return _installed(manifest, model.path);
  }

  Future<bool> _stamped(Directory d, ModelManifest m) async {
    try {
      final s = jsonDecode(await _stamp(d).readAsString()) as Map<String, dynamic>;
      final modified = (await _model(d).lastModified()).millisecondsSinceEpoch;
      return s['sha256'] == m.sha256 && s['bytes'] == m.bytes && s['modified'] == modified;
    } catch (_) {
      return false;
    }
  }

  Future<void> _writeStamp(Directory d, ModelManifest m, DateTime modified) => _stamp(d)
      .writeAsString(jsonEncode({'sha256': m.sha256, 'bytes': m.bytes, 'modified': modified.millisecondsSinceEpoch}));

  static InstalledModel _installed(ModelManifest m, String path) => InstalledModel(
      id: m.id, label: m.label, architecture: m.architecture, sha256: m.sha256, inputSize: m.inputSize,
      threshold: m.threshold, reviewBelow: m.reviewBelow, path: path, source: ModelSource.registry,
      validation: m.validation, validated: m.validated);

  static Future<String> _sha256(File f) async => (await sha256.bind(f.openRead()).first).toString();

  Future<String?> activeId() async {
    try {
      final v = (jsonDecode(await _active.readAsString()) as Map<String, dynamic>)['active'];
      return v is String ? v : null;
    } catch (_) {
      return null;
    }
  }

  /// Null clears the choice, so start-up falls back to the default model.
  Future<void> setActive(String? id) async {
    if (id == null) {
      if (await _active.exists()) await _active.delete();
      return;
    }
    await root.create(recursive: true);
    final tmp = File('${_active.path}.tmp');
    await tmp.writeAsString(jsonEncode({'active': id}), flush: true);
    await tmp.rename(_active.path);
  }

  Future<void> delete(String id) async {
    final d = _dir(id);
    if (id == defaultModelId || await _claimsDefault(d)) throw StateError('The default model cannot be deleted');
    if (await d.exists()) await d.delete(recursive: true);
    if (await activeId() == id) await setActive(null);
  }

  Future<bool> _claimsDefault(Directory d) async {
    try {
      return ModelManifest.parse(await _manifest(d).readAsString()).sha256 == defaultModelSha256;
    } catch (_) {
      return false;
    }
  }

  /// Copies [model] and [manifest] into the registry and enables the model only if its size and SHA-256
  /// match the manifest and [check] passes. Does not change the active model.
  Future<InstalledModel> importModel({required File model, required File manifest, required ModelCheck check}) async {
    final ModelManifest m;
    try {
      if (await manifest.length() > _maxManifestBytes) throw ManifestInvalid('file too large');
      m = ModelManifest.parse(await manifest.readAsString());
    } on ManifestInvalid catch (e) {
      throw ModelImportFailed(ImportFailure.manifestInvalid, e.detail);
    } on FileSystemException catch (e) {
      throw ModelImportFailed(ImportFailure.unreadable, e.message);
    }
    return _install(m, (staged) => model.copy(staged.path), check);
  }

  /// True when a model folder with this id exists (whether or not it verifies).
  Future<bool> has(String id) => _dir(id).exists();

  /// Where a download of [id] is streamed before [installDownloaded]; inside [root] so the install can
  /// rename it rather than copy it, and a dot-file so [list] never reads it.
  File downloadPart(String id) => File('${root.path}$_sep.download-$id.part');

  /// Installs a downloaded file (typically [downloadPart]) with its catalogue manifest, through the same
  /// size, SHA-256 and [check] steps as [importModel]. The file is moved, not copied. Does not change the
  /// active model.
  Future<InstalledModel> installDownloaded({required File part, required ModelManifest manifest,
          required ModelCheck check}) =>
      _install(manifest, (staged) => part.rename(staged.path), check);

  /// Places the model file into a staging folder with [place], verifies it, then moves the folder into
  /// place. Any failure deletes the staging folder.
  Future<InstalledModel> _install(ModelManifest m, Future<File> Function(File staged) place, ModelCheck check) async {
    final target = _dir(m.id);
    if (await target.exists()) throw ModelImportFailed(ImportFailure.alreadyInstalled, m.id);

    final staging = Directory('${root.path}$_sep.import-${m.id}');
    try {
      if (await staging.exists()) await staging.delete(recursive: true);
      await staging.create(recursive: true);
      final staged = _model(staging);
      try {
        await place(staged);
        await _manifest(staging).writeAsString(jsonEncode(m.toJson()), flush: true);
      } on FileSystemException catch (e) {
        throw ModelImportFailed(ImportFailure.unreadable, e.message);
      }
      final size = await staged.length();
      if (size != m.bytes) throw ModelImportFailed(ImportFailure.sizeMismatch, 'got $size bytes, expected ${m.bytes}');
      final digest = await _sha256(staged);
      if (digest != m.sha256) throw ModelImportFailed(ImportFailure.checksumMismatch, 'got $digest');
      try {
        await check(staged.path, m);
      } on ModelImportFailed {
        rethrow;
      } catch (e) {
        throw ModelImportFailed(ImportFailure.selfTestFailed, '$e');
      }
      await _writeStamp(staging, m, await staged.lastModified());
      await staging.rename(target.path);
      return _installed(m, _model(target).path);
    } catch (_) {
      if (await staging.exists()) await staging.delete(recursive: true);
      rethrow;
    }
  }
}
