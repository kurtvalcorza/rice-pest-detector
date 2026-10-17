// Installed models: one folder per model (model.onnx + manifest.json) plus the active model id.
// Import verifies size, SHA-256 and the caller's session check before the model is enabled, and a
// failure leaves nothing behind.
import 'dart:convert';
import 'dart:io';

import 'package:crypto/crypto.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:rice_pest_app/model/model_manifest.dart';
import 'package:rice_pest_app/model/model_registry.dart';

String sep = Platform.pathSeparator;

Map<String, dynamic> manifestFor(List<int> payload, {String id = 'rfdetr-m', String? sha, int? bytes}) => {
      'id': id, 'label': id.toUpperCase(), 'architecture': 'RF-DETR', 'base_model': 'Roboflow/rf-detr-medium',
      'licence': 'Apache-2.0', 'input_size': 576, 'threshold': 0.48, 'review_below': 0.63,
      'sha256': sha ?? sha256.convert(payload).toString(), 'bytes': bytes ?? payload.length,
      'outputs': ['logits', 'pred_boxes'], 'num_classes': 4,
      'validation': {'count_accuracy': 0.846, 'species_map50': 0.933, 'wsb30_mae': 9.56}, 'validated': false,
    };

Future<void> passes(String path, ModelManifest m) async {}

void main() {
  late Directory root;
  late Directory picked;
  final payload = utf8.encode('pretend onnx bytes');

  setUp(() {
    root = Directory.systemTemp.createTempSync('registry ');
    picked = Directory('${root.path}${sep}picked')..createSync();
  });
  tearDown(() => root.deleteSync(recursive: true));

  ModelRegistry registry() => ModelRegistry(Directory('${root.path}${sep}models'));

  (File, File) files({List<int>? onnx, Map<String, dynamic>? manifest, String name = 'm'}) {
    final model = File('${picked.path}$sep$name.onnx')..writeAsBytesSync(onnx ?? payload);
    final man = File('${picked.path}$sep$name.json')..writeAsStringSync(jsonEncode(manifest ?? manifestFor(payload)));
    return (model, man);
  }

  List<String> leftovers() =>
      registry().root.existsSync() ? registry().root.listSync().map((e) => e.uri.pathSegments.where((s) => s.isNotEmpty).last).toList() : [];

  test('an imported model is copied into its own folder and listed with its manifest values', () async {
    final (model, man) = files();
    final r = registry();
    final m = await r.importModel(model: model, manifest: man, check: passes);
    expect([m.id, m.label, m.inputSize, m.threshold, m.reviewBelow, m.source], ['rfdetr-m', 'RFDETR-M', 576, 0.48, 0.63,
        ModelSource.registry]);
    expect(File(m.path).readAsBytesSync(), payload);
    expect(m.path, endsWith('models${sep}rfdetr-m${sep}model.onnx'));
    expect(File('${registry().root.path}${sep}rfdetr-m${sep}manifest.json').existsSync(), isTrue);
    final listed = await registry().list();
    expect(listed.single.id, 'rfdetr-m');
    expect(listed.single.validation!.countAccuracy, 0.846);
    expect(listed.single.validated, isFalse);
    expect(listed.single.isDefault, isFalse);
    expect(listed.single.deletable, isTrue);
  });

  test('import does not change the active model', () async {
    final r = registry();
    await r.setActive('r50-v5');
    final (model, man) = files();
    await r.importModel(model: model, manifest: man, check: passes);
    expect(await registry().activeId(), 'r50-v5');
  });

  test('a wrong size is rejected and nothing is left behind', () async {
    final (model, man) = files(manifest: manifestFor(payload, bytes: payload.length + 1));
    await expectLater(registry().importModel(model: model, manifest: man, check: passes),
        throwsA(isA<ModelImportFailed>().having((e) => e.reason, 'reason', ImportFailure.sizeMismatch)));
    expect(leftovers(), isEmpty);
    expect(await registry().list(), isEmpty);
  });

  test('a wrong SHA-256 is rejected and nothing is left behind', () async {
    final (model, man) = files(manifest: manifestFor(payload, sha: sha256.convert([1]).toString()));
    await expectLater(registry().importModel(model: model, manifest: man, check: passes),
        throwsA(isA<ModelImportFailed>().having((e) => e.reason, 'reason', ImportFailure.checksumMismatch)));
    expect(leftovers(), isEmpty);
  });

  test('an invalid manifest is rejected before anything is copied', () async {
    final (model, _) = files();
    final bad = File('${picked.path}${sep}bad.json')..writeAsStringSync('{"id": "x"}');
    await expectLater(registry().importModel(model: model, manifest: bad, check: (_, _) => fail('no check')),
        throwsA(isA<ModelImportFailed>().having((e) => e.reason, 'reason', ImportFailure.manifestInvalid)));
    expect(leftovers(), isEmpty);
  });

  test('a failed session check (shape or self-test) rolls back and keeps the previous active model', () async {
    final r = registry();
    await r.setActive('r50-v5');
    for (final reason in [ImportFailure.shapeMismatch, ImportFailure.selfTestFailed]) {
      final (model, man) = files();
      await expectLater(
          r.importModel(model: model, manifest: man, check: (_, _) async => throw ModelImportFailed(reason, 'test')),
          throwsA(isA<ModelImportFailed>().having((e) => e.reason, 'reason', reason)));
      expect(leftovers(), ['active.json']);
    }
    expect(await r.activeId(), 'r50-v5');
  });

  test('any other error from the session check counts as a failed self-test', () async {
    final (model, man) = files();
    await expectLater(registry().importModel(model: model, manifest: man, check: (_, _) async => throw StateError('ort')),
        throwsA(isA<ModelImportFailed>().having((e) => e.reason, 'reason', ImportFailure.selfTestFailed)));
    expect(leftovers(), isEmpty);
  });

  test('the session check sees the copied file, not the picked one', () async {
    final (model, man) = files();
    String? seen;
    await registry().importModel(model: model, manifest: man, check: (p, m) async => seen = p);
    expect(seen, isNot(model.path));
    expect(seen, contains('models'));
  });

  test('a second model with the same id is refused and the first is kept', () async {
    final r = registry();
    final (model, man) = files();
    await r.importModel(model: model, manifest: man, check: passes);
    final (model2, man2) = files(onnx: [...payload, 1], manifest: manifestFor([...payload, 1]), name: 'n');
    await expectLater(r.importModel(model: model2, manifest: man2, check: passes),
        throwsA(isA<ModelImportFailed>().having((e) => e.reason, 'reason', ImportFailure.alreadyInstalled)));
    expect(File((await r.list()).single.path).readAsBytesSync(), payload);
  });

  test('the active id persists across instances and can be cleared', () async {
    expect(await registry().activeId(), isNull);
    await registry().setActive('rfdetr-m');
    expect(await registry().activeId(), 'rfdetr-m');
    await registry().setActive(null);
    expect(await registry().activeId(), isNull);
  });

  test('a corrupt active file reads as no active model', () async {
    await registry().setActive('x');
    File('${registry().root.path}${sep}active.json').writeAsStringSync('{oops');
    expect(await registry().activeId(), isNull);
  });

  test('deleting a model removes its folder and clears it as active', () async {
    final r = registry();
    final (model, man) = files();
    await r.importModel(model: model, manifest: man, check: passes);
    await r.setActive('rfdetr-m');
    await r.delete('rfdetr-m');
    expect(await r.list(), isEmpty);
    expect(await r.activeId(), isNull);
    expect(Directory('${r.root.path}${sep}rfdetr-m').existsSync(), isFalse);
  });

  test('the default model (by its SHA-256) cannot be deleted', () async {
    final r = registry();
    final dir = Directory('${r.root.path}${sep}r50-v5')..createSync(recursive: true);
    File('${dir.path}${sep}model.onnx').writeAsBytesSync(payload);
    // A manifest that claims the default SHA-256 but whose file does not match is not listed at all.
    File('${dir.path}${sep}manifest.json').writeAsStringSync(jsonEncode(manifestFor(payload, id: 'r50-v5',
        sha: defaultModelSha256)));
    expect(await r.list(), isEmpty);
    await expectLater(r.delete('r50-v5'), throwsA(isA<StateError>()));
    expect(dir.existsSync(), isTrue);
  });

  test('a model placed by hand is listed only once its SHA-256 matches, then remembered', () async {
    final r = registry();
    final dir = Directory('${r.root.path}${sep}dfine-l')..createSync(recursive: true);
    File('${dir.path}${sep}model.onnx').writeAsBytesSync(payload);
    File('${dir.path}${sep}manifest.json').writeAsStringSync(jsonEncode(manifestFor(payload, id: 'dfine-l')));
    expect((await r.list()).single.id, 'dfine-l');
    File('${dir.path}${sep}model.onnx').writeAsBytesSync([...payload.reversed]); // same size, different bytes
    expect(await r.list(), isEmpty, reason: 'the stamp records the verified SHA-256, so a changed file is caught');
  });

  test('folders without a valid manifest or file are skipped, not fatal', () async {
    final r = registry();
    Directory('${r.root.path}${sep}empty').createSync(recursive: true);
    final dir = Directory('${r.root.path}${sep}junk')..createSync(recursive: true);
    File('${dir.path}${sep}manifest.json').writeAsStringSync('{not json');
    final (model, man) = files();
    await r.importModel(model: model, manifest: man, check: passes);
    expect((await r.list()).map((m) => m.id), ['rfdetr-m']);
  });

  test('the listed order puts the default model first, then by label', () async {
    expect(sortModels([
      InstalledModel(id: 'b', label: 'B', sha256: 'x', inputSize: 640, threshold: .5, reviewBelow: .6, path: 'p',
          source: ModelSource.registry),
      InstalledModel(id: 'z', label: 'A', sha256: defaultModelSha256, inputSize: 640, threshold: .5, reviewBelow: .6,
          path: 'p', source: ModelSource.pin),
      InstalledModel(id: 'a', label: 'C', sha256: 'y', inputSize: 640, threshold: .5, reviewBelow: .6, path: 'p',
          source: ModelSource.registry),
    ]).map((m) => m.id), ['z', 'b', 'a']);
  });
}
