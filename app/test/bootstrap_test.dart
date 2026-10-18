import 'dart:convert';
import 'dart:io';

import 'package:crypto/crypto.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:rice_pest_app/app/bootstrap.dart';
import 'package:rice_pest_app/app/services.dart';
import 'package:rice_pest_app/counting/counting.dart';
import 'package:rice_pest_app/inference/contract.dart';
import 'package:rice_pest_app/inference/detector.dart';
import 'package:rice_pest_app/model/model_registry.dart';
import 'package:rice_pest_app/model/model_store.dart';

class _Probe implements Detector {
  _Probe(this.modelId, this.inputSize);
  @override
  final String modelId;
  final int inputSize;
  @override
  Future<List<Never>> detect(PhotoRef photo) async => [];
}

void main() {
  late Directory root;
  final sep = Platform.pathSeparator;
  final payload = utf8.encode('pretend onnx bytes');
  final sha = sha256.convert(payload).toString();
  ModelPin pin({String kind = 'published', double? threshold, String label = ''}) =>
      ModelPin('https://example.invalid/m.onnx', sha, payload.length, threshold: threshold, label: label, kind: kind);
  Future<Detector> load(InstalledModel m) async => _Probe(m.label, m.inputSize);

  setUp(() => root = Directory.systemTemp.createTempSync('bootstrap '));
  tearDown(() => root.deleteSync(recursive: true));

  ModelStore store(String name) => ModelStore(Directory('${root.path}$sep$name'));
  File demoMeta() => File('${root.path}${sep}demo${sep}demo.json');
  ModelRegistry registry() => ModelRegistry(Directory('${root.path}${sep}models'));

  Future<void> install(ModelStore s) async {
    await s.dir.create(recursive: true);
    await s.modelFile.writeAsBytes(payload);
  }

  /// Places a model in the registry as an import would leave it.
  Future<void> register(String id, List<int> bytes, {int inputSize = 640, double threshold = 0.48,
      double reviewBelow = 0.64, bool validated = false}) async {
    final dir = Directory('${registry().root.path}$sep$id')..createSync(recursive: true);
    File('${dir.path}${sep}model.onnx').writeAsBytesSync(bytes);
    File('${dir.path}${sep}manifest.json').writeAsStringSync(jsonEncode({
      'id': id, 'label': id.toUpperCase(), 'architecture': 'x', 'base_model': 'x', 'licence': 'Apache-2.0',
      'input_size': inputSize, 'threshold': threshold, 'review_below': reviewBelow,
      'sha256': sha256.convert(bytes).toString(), 'bytes': bytes.length, 'outputs': ['logits', 'pred_boxes'],
      'num_classes': 4, 'validation': {'count_accuracy': 0.8, 'species_map50': 0.9, 'wsb30_mae': 9.0},
      'validated': validated,
    }));
  }

  Future<ModelChoice> choose({ModelPin? p, bool withRegistry = true}) => chooseModel(
      pin: p ?? const ModelPin('', '', 0), store: store('model'), demoStore: store('demo'), demoMeta: demoMeta(),
      registry: withRegistry ? registry() : null, load: load);

  test('an installed demo pin runs in demo mode at the pin threshold, under its label', () async {
    final s = store('model');
    await install(s);
    final c = await chooseModel(pin: pin(kind: 'demo', threshold: 0.04, label: 'r50-v5-demo'), store: s,
        demoStore: store('demo'), demoMeta: demoMeta(), load: load);
    expect([c.mode, c.threshold, c.detector!.modelId, c.canDownload], [ModelMode.demo, 0.04, 'r50-v5-demo', false]);
    expect([c.active!.source, c.active!.inputSize, c.reviewBelow], [ModelSource.pin, inputSize, defaultReviewBelow]);
  });

  test('an installed published pin without a threshold uses the contract default', () async {
    final s = store('model');
    await install(s);
    final c = await chooseModel(pin: pin(), store: s, demoStore: store('demo'), demoMeta: demoMeta(), load: load);
    expect([c.mode, c.threshold], [ModelMode.published, defaultThreshold]);
  });

  test('a set pin that is not installed offers the download and does not count', () async {
    final c = await chooseModel(pin: pin(kind: 'demo', threshold: 0.04), store: store('model'),
        demoStore: store('demo'), demoMeta: demoMeta(), load: load);
    expect([c.mode, c.detector, c.canDownload, c.active], [ModelMode.none, null, true, null]);
  });

  test('an empty pin offers nothing', () async {
    final c = await chooseModel(pin: const ModelPin('', '', 0), store: store('model'), demoStore: store('demo'),
        demoMeta: demoMeta(), load: load);
    expect([c.mode, c.canDownload], [ModelMode.none, false]);
  });

  test('a demo.json side-load still works, in demo mode at its threshold', () async {
    await install(store('demo'));
    demoMeta().writeAsStringSync(jsonEncode({'sha256': sha, 'bytes': payload.length, 'threshold': 0.48,
        'label': 'side-loaded'}));
    final c = await choose();
    expect([c.mode, c.threshold, c.detector!.modelId, c.active!.source], [ModelMode.demo, 0.48, 'side-loaded',
        ModelSource.sideloaded]);
  });

  test('the active registry model wins, with its own input size, threshold and review flag', () async {
    await install(store('demo'));
    demoMeta().writeAsStringSync(jsonEncode({'sha256': sha, 'bytes': payload.length, 'threshold': 0.48,
        'label': 'side-loaded'}));
    await register('rfdetr-m', [1, 2, 3], inputSize: 576, threshold: 0.48, reviewBelow: 0.63);
    await registry().setActive('rfdetr-m');
    final c = await choose();
    final probe = c.detector! as _Probe;
    expect([probe.modelId, probe.inputSize, c.threshold, c.reviewBelow, c.mode], ['RFDETR-M', 576, 0.48, 0.63,
        ModelMode.demo]);
    expect(c.active!.isDefault, isFalse);
  });

  test('a validated registry model runs in published mode', () async {
    await register('ok', [9], validated: true);
    await registry().setActive('ok');
    expect((await choose()).mode, ModelMode.published);
  });

  test('without an active choice, a non-default registry model is never picked on its own', () async {
    await register('rfdetr-m', [1, 2, 3]);
    final c = await choose();
    expect([c.mode, c.detector], [ModelMode.none, null]);
  });

  test('an active id that is no longer installed falls back to the default model', () async {
    await register('rfdetr-m', [1, 2, 3]);
    await register('dflt', payload);
    await registry().setActive('gone');
    final c = await chooseModel(pin: const ModelPin('', '', 0), store: store('model'), demoStore: store('demo'),
        demoMeta: demoMeta(), registry: registry(), load: load, defaultSha256: sha);
    expect([c.active!.id, c.active!.isDefault], ['dflt', false],
        reason: 'isDefault uses the shipped default SHA-256; defaultSha256 only steers the fallback here');
  });

  test('the old pin still wins over a non-active registry model', () async {
    await install(store('model'));
    await register('rfdetr-m', [1, 2, 3]);
    final c = await choose(p: pin(kind: 'demo', threshold: 0.48, label: 'r50-v5-demo'));
    expect([c.detector!.modelId, c.active!.source], ['r50-v5-demo', ModelSource.pin]);
  });

  test('a legacy pin can be made active by its id and back again', () async {
    await install(store('model'));
    await register('rfdetr-m', [1, 2, 3]);
    await registry().setActive('rfdetr-m');
    final p = pin(kind: 'demo', threshold: 0.48, label: 'r50-v5-demo');
    expect((await choose(p: p)).active!.id, 'rfdetr-m');
    await registry().setActive('r50-v5-demo');
    expect((await choose(p: p)).active!.id, 'r50-v5-demo');
  });

  test('installedModels lists registry, pin and side-loaded models together', () async {
    await install(store('model'));
    final dev = utf8.encode('other onnx bytes');
    await store('demo').dir.create(recursive: true);
    await store('demo').modelFile.writeAsBytes(dev);
    demoMeta().writeAsStringSync(jsonEncode({'sha256': sha256.convert(dev).toString(), 'bytes': dev.length,
        'threshold': 0.4, 'label': 'dev'}));
    await register('rfdetr-m', [1, 2, 3]);
    final all = await installedModels(pin: pin(label: 'pinned'), store: store('model'), demoStore: store('demo'),
        demoMeta: demoMeta(), registry: registry());
    expect(all.map((m) => m.id).toSet(), {'rfdetr-m', 'pinned', 'dev'});
    expect(all.where((m) => m.deletable).map((m) => m.id), ['rfdetr-m']);
  });

  test('a side-loaded copy of a downloaded model is listed once, as the download', () async {
    await register('r50-v5', payload);
    await install(store('demo'));
    demoMeta().writeAsStringSync(jsonEncode({'sha256': sha, 'bytes': payload.length, 'threshold': 0.48,
        'label': 'r50-v5-demo'}));
    final all = await installedModels(pin: const ModelPin('', '', 0), store: store('model'), demoStore: store('demo'),
        demoMeta: demoMeta(), registry: registry());
    expect(all.map((m) => m.id), ['r50-v5']);
  });
}
