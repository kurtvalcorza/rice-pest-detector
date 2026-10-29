// Which model the app runs at start-up, and whether it can offer a download.
// Installed models come from three places: the model registry (imported models, one folder each), the
// pinned download, and a developer-placed demo model (demo/demo.json, adb). Order: the model the user
// made active in Settings, if installed; else the default model (r50-v5, by SHA-256); else the pinned
// model; else the side-loaded demo; else no model. A pin that is set but not installed is offered for
// download; the app does not count until a verified file is in place. A non-default model is used only
// when it was made active.
import 'dart:convert';
import 'dart:io';

import '../counting/counting.dart';
import '../inference/contract.dart';
import '../inference/detector.dart';
import '../model/model_registry.dart';
import '../model/model_store.dart';
import 'services.dart';

typedef DetectorLoader = Future<Detector> Function(InstalledModel model);

class ModelChoice {
  const ModelChoice(this.mode, this.detector, this.threshold,
      {this.canDownload = false, this.active, this.reviewBelow = defaultReviewBelow});
  final ModelMode mode;
  final Detector? detector;
  final double threshold;
  final double reviewBelow;

  /// The model behind [detector]; null in [ModelMode.none].
  final InstalledModel? active;

  /// The pin is set but its file is not installed: the home screen offers the download.
  final bool canDownload;
}

/// The pinned model, if its file is installed and verified, as a registry-style entry.
Future<InstalledModel?> _pinned(ModelPin pin, ModelStore store) async {
  if (!await store.isInstalled(pin)) return null;
  final id = pin.label.isNotEmpty ? pin.label : pin.sha256.substring(0, 12);
  return InstalledModel(id: id, label: id, sha256: pin.sha256, inputSize: inputSize,
      threshold: pin.threshold ?? defaultThreshold, reviewBelow: defaultReviewBelow, path: store.modelFile.path,
      source: ModelSource.pin, published: !pin.isDemo);
}

/// A developer's side-loaded demo model (demo/rice-pest.onnx + demo/demo.json), if it verifies.
Future<InstalledModel?> _sideloaded(ModelStore demoStore, File demoMeta) async {
  if (!await demoMeta.exists()) return null;
  final ModelPin local;
  final String label;
  final double threshold;
  try {
    final meta = jsonDecode(await demoMeta.readAsString()) as Map<String, dynamic>;
    local = ModelPin('local-demo', meta['sha256'] as String, (meta['bytes'] as num).toInt());
    label = meta['label'] as String;
    threshold = (meta['threshold'] as num).toDouble();
  } on FormatException {
    return null; // not JSON: ignored, so a bad hand-placed file cannot stop the app starting
  } on TypeError {
    return null;
  }
  if (!await demoStore.isInstalled(local)) return null;
  return InstalledModel(id: label, label: label, sha256: local.sha256, inputSize: inputSize,
      threshold: threshold, reviewBelow: defaultReviewBelow, path: demoStore.modelFile.path,
      source: ModelSource.sideloaded);
}

/// The registry lists a model by a size-and-time stamp written when it was verified, so the file is
/// hashed again before it is opened. (The pin and the side-loaded demo are hashed whenever they are listed.)
Future<bool> stillMatches(InstalledModel m) async =>
    m.source != ModelSource.registry || await fileSha256(File(m.path)) == m.sha256;

/// Every installed model, registry first; a legacy entry whose id or file (SHA-256) is already listed is dropped,
/// so a side-loaded copy of a downloaded model appears once.
Future<List<InstalledModel>> installedModels({required ModelPin pin, required ModelStore store,
    required ModelStore demoStore, required File demoMeta, ModelRegistry? registry}) async {
  final all = [...?await registry?.list()];
  for (final legacy in [await _pinned(pin, store), await _sideloaded(demoStore, demoMeta)]) {
    if (legacy != null && all.every((m) => m.id != legacy.id && m.sha256 != legacy.sha256)) all.add(legacy);
  }
  return sortModels(all);
}

Future<ModelChoice> chooseModel({
  required ModelPin pin,
  required ModelStore store,
  required ModelStore demoStore,
  required File demoMeta,
  ModelRegistry? registry,
  required DetectorLoader load,
  String defaultSha256 = defaultModelSha256,
}) async {
  final all = await installedModels(pin: pin, store: store, demoStore: demoStore, demoMeta: demoMeta,
      registry: registry);
  final activeId = await registry?.activeId();
  InstalledModel? pick(bool Function(InstalledModel) test) {
    for (final m in all) {
      if (test(m)) return m;
    }
    return null;
  }

  for (final chosen in [
    pick((m) => m.id == activeId),
    pick((m) => m.sha256 == defaultSha256),
    pick((m) => m.source == ModelSource.pin),
    pick((m) => m.source == ModelSource.sideloaded),
  ]) {
    if (chosen == null || !await stillMatches(chosen)) continue; // a changed file falls through to the next
    final mode = chosen.published || chosen.validated ? ModelMode.published : ModelMode.demo;
    return ModelChoice(mode, await load(chosen), chosen.threshold, active: chosen, reviewBelow: chosen.reviewBelow);
  }
  return ModelChoice(ModelMode.none, null, defaultThreshold, canDownload: pin.isSet);
}
