import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:path_provider/path_provider.dart';

import 'app/app.dart';
import 'app/bootstrap.dart';
import 'app/model_catalog.dart';
import 'app/platform_services.dart';
import 'app/services.dart';
import 'inference/detector.dart';
import 'inference/model_check.dart';
import 'inference/onnx_detector.dart';
import 'model/model_registry.dart';
import 'model/model_store.dart';
import 'model/published_models.dart';
import 'storage/history.dart';

const modelPinAsset = 'assets/model_pin.json';
const modelCatalogAsset = 'assets/model_catalog.json';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  final docs = await getApplicationDocumentsDirectory();
  String sub(String name) => '${docs.path}${Platform.pathSeparator}$name';

  // The pin names one model file (URL, size, SHA-256) with its own threshold and kind (demo or
  // published). It is downloaded only when the user asks, and used only once verified. A developer can
  // still place a demo model by hand: demo/rice-pest.onnx plus demo/demo.json. Other models are imported
  // in Settings from a .onnx file and its manifest, or downloaded from the bundled catalogue, verified, and
  // kept in models/<id>/.
  final pin = ModelPin.fromJson(await rootBundle.loadString(modelPinAsset));
  final store = ModelStore(Directory(sub('model')));
  final demoStore = ModelStore(Directory(sub('demo')));
  final demoMeta = File(sub('demo${Platform.pathSeparator}demo.json'));
  final registry = ModelRegistry(Directory(sub('models')));
  final history = HistoryStore(Directory(sub('history')));
  final photos = ImagePickerSource(Directory(sub('photos')));
  final sharer = SharePlusSharer();

  Future<Detector> load(InstalledModel m) =>
      OnnxDetector.fromFile(m.path, modelId: m.label, inputSize: m.inputSize);
  Future<void> unload(Detector d) async {
    if (d is OnnxDetector) await d.close();
  }

  // The published models Settings offers for download (fetched only when the user taps Download).
  final published = parsePublishedModels(await rootBundle.loadString(modelCatalogAsset));
  final catalog = LocalModelCatalog(
      registry: registry, pin: pin, store: store, demoStore: demoStore, demoMeta: demoMeta, load: load,
      unload: unload, check: (path, manifest) => checkModel(OnnxProbe(), path, manifest), published: published);
  final modelFiles = FileSelectorModelFiles();

  Future<AppServices> bootstrap() async {
    final choice = await chooseModel(
        pin: pin, store: store, demoStore: demoStore, demoMeta: demoMeta, registry: registry, load: load);
    final detector = choice.detector;
    return AppServices(
      detector: detector,
      history: history,
      photos: photos,
      sharer: sharer,
      mode: choice.mode,
      threshold: choice.threshold,
      reviewBelow: choice.reviewBelow,
      activeModel: choice.active,
      models: catalog,
      modelFiles: modelFiles,
      release: detector == null ? null : () => unload(detector),
      download: choice.canDownload
          ? ModelDownload(bytes: pin.bytes, label: pin.label, run: () async => store.download(pin))
          : null,
    );
  }

  runApp(RicePestApp(services: await bootstrap(), reload: bootstrap));
}
