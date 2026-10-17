// Settings → Model: the always-visible model switcher, import, delete, the compare screen, and the
// "Demo model, not validated" banner for every model that is not the default.
import 'dart:async';
import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:rice_pest_app/app/app.dart';
import 'package:rice_pest_app/app/services.dart';
import 'package:rice_pest_app/inference/detector.dart';
import 'package:rice_pest_app/inference/postprocess.dart';
import 'package:rice_pest_app/model/model_manifest.dart';
import 'package:rice_pest_app/model/model_registry.dart';
import 'package:rice_pest_app/model/model_store.dart';
import 'package:rice_pest_app/model/published_models.dart';

import 'l10n_test.dart' show treatmentWords;
import 'ui_test.dart' show FakePhotos, MemoryHistory, RecordingSharer;

const banner = 'Demo model, not validated. Use its counts only for comparison with the default model.';

InstalledModel model(String id, String label, {bool isDefault = false, int inputSize = 640, double threshold = 0.48,
        double reviewBelow = 0.64, double accuracy = 0.8, ModelSource source = ModelSource.registry}) =>
    InstalledModel(
        id: id, label: label, architecture: '$label arch', sha256: isDefault ? defaultModelSha256 : 'f' * 64,
        inputSize: inputSize, threshold: threshold, reviewBelow: reviewBelow, path: '/models/$id/model.onnx',
        source: source, validation: ModelValidation(countAccuracy: accuracy, speciesMap50: 0.9, wsb30Mae: 9));

final r50 = model('r50-v5', 'r50-v5', isDefault: true, accuracy: 0.834);
final rf = model('rfdetr-m', 'RF-DETR-M', inputSize: 576, threshold: 0.48, reviewBelow: 0.63, accuracy: 0.846);
final df = model('dfine-l', 'D-FINE-L', threshold: 0.50, reviewBelow: 0.68, accuracy: 0.822);

/// Scores fixed per model so the compare screen shows different counts.
class ScoreDetector implements Detector {
  ScoreDetector(this.modelId, this.scores);
  @override
  final String modelId;
  final List<(int, double)> scores;
  @override
  Future<List<Detection>> detect(PhotoRef photo) async =>
      [for (final (c, s) in scores) Detection(c, s, 0, 0, 1, 1)]..sort((a, b) => b.score.compareTo(a.score));
}

final detections = <String, List<(int, double)>>{
  'r50-v5': [(0, 0.9), (0, 0.5), (2, 0.7)], // RBB 2, WSB 1, one under 0.64
  'rfdetr-m': [(0, 0.9), (2, 0.7), (2, 0.66)], // RBB 1, WSB 2, none under 0.63
  'dfine-l': [(0, 0.49), (3, 0.95)], // RBB 0 at 0.50, WSB 1
};

class FakeCatalog implements ModelCatalog {
  FakeCatalog(this.models);
  List<InstalledModel> models;
  final activated = <String?>[];
  final deleted = <String>[];
  final opened = <String>[];
  final closed = <String>[];
  int openNow = 0, maxOpen = 0;
  Object? importError;
  (File, File)? imported;

  @override
  Future<List<InstalledModel>> list() async => models;
  @override
  Future<void> activate(String? id) async => activated.add(id);
  @override
  Future<void> delete(String id) async {
    deleted.add(id);
    models = [for (final m in models) if (m.id != id) m];
  }

  @override
  Future<InstalledModel> importFrom({required File model, required File manifest}) async {
    imported = (model, manifest);
    if (importError != null) throw importError!;
    models = [...models, df];
    return df;
  }

  @override
  List<PublishedModel> published = [];
  final downloaded = <String>[];
  Object? downloadError;
  List<(int, int?)> progressSteps = [];

  /// When set, a download waits for it (or for a cancel) after reporting its progress.
  Completer<void>? downloadGate;
  InstalledModel? downloadResult;

  @override
  Future<InstalledModel> download(PublishedModel p,
      {void Function(int received, int? total)? onProgress, DownloadCancel? cancel}) async {
    downloaded.add(p.manifest.id);
    for (final (r, t) in progressSteps) {
      onProgress?.call(r, t);
    }
    final gate = downloadGate;
    if (gate != null) {
      await Future.any([gate.future, if (cancel != null) cancel.whenCancelled]);
      if (cancel?.isCancelled ?? false) throw DownloadCancelled();
    }
    if (downloadError != null) throw downloadError!;
    final m = downloadResult!;
    models = [...models, m];
    return m;
  }

  @override
  Future<Detector> open(InstalledModel m) async {
    opened.add(m.id);
    final scores = detections[m.id];
    if (scores == null) throw StateError('cannot open ${m.id}');
    maxOpen = ++openNow > maxOpen ? openNow : maxOpen;
    return ScoreDetector(m.label, scores);
  }

  @override
  Future<void> close(Detector d) async {
    openNow--;
    closed.add(d.modelId);
  }
}

class FakeModelFiles implements ModelFilePicker {
  FakeModelFiles({this.manifest, this.model});
  File? manifest, model;
  @override
  Future<File?> pickManifest() async => manifest;
  @override
  Future<File?> pickModel() async => model;
}

AppServices servicesWith(InstalledModel? active, ModelCatalog catalog,
        {MemoryHistory? history, RecordingSharer? sharer, ModelFilePicker? files, PhotoRef? photo}) =>
    AppServices(
      detector: active == null ? null : ScoreDetector(active.label, detections[active.id]!),
      history: history ?? MemoryHistory(),
      photos: FakePhotos(photo ?? const PhotoRef('trap-1.jpg', '/photos/trap-1.jpg')),
      sharer: sharer ?? RecordingSharer(),
      mode: active == null ? ModelMode.none : ModelMode.demo,
      threshold: active?.threshold ?? 0.5,
      reviewBelow: active?.reviewBelow ?? 0.64,
      activeModel: active,
      models: catalog,
      modelFiles: files ?? FakeModelFiles(),
      now: () => DateTime(2026, 10, 18, 7, 5),
      newId: () => 'id-1',
    );

/// A tall screen, so every comparison card is built without scrolling.
void tallScreen(WidgetTester tester) {
  tester.view.physicalSize = const Size(1080, 4000);
  tester.view.devicePixelRatio = 1;
  addTearDown(tester.view.reset);
}

Future<void> openSettings(WidgetTester tester) async {
  await tester.tap(find.byTooltip('Settings'));
  await tester.pumpAndSettle();
}

void main() {
  testWidgets('the default model shows no banner; the settings button is always there', (tester) async {
    await tester.pumpWidget(RicePestApp(services: servicesWith(r50, FakeCatalog([r50, rf]))));
    await tester.pumpAndSettle();
    expect(find.text(banner), findsNothing);
    expect(find.byTooltip('Settings'), findsOneWidget);
  });

  testWidgets('settings is reachable even with no model installed', (tester) async {
    await tester.pumpWidget(RicePestApp(services: servicesWith(null, FakeCatalog([]))));
    await tester.pumpAndSettle();
    await openSettings(tester);
    expect(find.text('No models are installed.'), findsOneWidget);
    expect(find.text('Import a model from a file'), findsOneWidget);
  });

  testWidgets('settings lists each model with its facts and tags', (tester) async {
    await tester.pumpWidget(RicePestApp(services: servicesWith(r50, FakeCatalog([r50, rf]))));
    await tester.pumpAndSettle();
    await openSettings(tester);
    expect(find.text('Model'), findsOneWidget);
    expect(find.text('r50-v5'), findsOneWidget);
    expect(find.text('RF-DETR-M'), findsOneWidget);
    expect(find.text('RF-DETR-M arch · 576 px · threshold 0.48 · count accuracy 0.846'), findsOneWidget);
    expect(find.text('r50-v5 arch · 640 px · threshold 0.48 · count accuracy 0.834'), findsOneWidget);
    expect(find.descendant(of: find.byKey(const Key('model-r50-v5')), matching: find.text('Default')), findsOneWidget);
    expect(find.descendant(of: find.byKey(const Key('model-r50-v5')), matching: find.text('In use')), findsOneWidget);
    expect(find.descendant(of: find.byKey(const Key('model-rfdetr-m')), matching: find.text('In use')), findsNothing);
    expect(find.text('Not validated'), findsNWidgets(2));
    // Only an imported model that is not the default can be deleted.
    expect(find.descendant(of: find.byKey(const Key('model-r50-v5')), matching: find.byIcon(Icons.delete_outline)),
        findsNothing);
    expect(find.descendant(of: find.byKey(const Key('model-rfdetr-m')), matching: find.byIcon(Icons.delete_outline)),
        findsOneWidget);
  });

  testWidgets('tapping a model makes it active, reloads, and the home screen then shows the banner', (tester) async {
    final catalog = FakeCatalog([r50, rf]);
    var reloads = 0;
    await tester.pumpWidget(RicePestApp(
        services: servicesWith(r50, catalog),
        reload: () async {
          reloads++;
          return servicesWith(rf, catalog);
        }));
    await tester.pumpAndSettle();
    await openSettings(tester);
    await tester.tap(find.text('RF-DETR-M'));
    await tester.pumpAndSettle();
    expect(catalog.activated, ['rfdetr-m']);
    expect(reloads, 1);
    expect(find.text('Now using RF-DETR-M.'), findsOneWidget);
    expect(find.text(banner), findsOneWidget);
    expect(find.text('Take a photo of the trap'), findsOneWidget, reason: 'back on the home screen');
  });

  testWidgets('if the new model fails to load, the previous choice is restored and the app says so', (tester) async {
    final catalog = FakeCatalog([r50, rf]);
    await tester.pumpWidget(RicePestApp(
        services: servicesWith(r50, catalog), reload: () async => throw StateError('ORT could not open')));
    await tester.pumpAndSettle();
    await openSettings(tester);
    await tester.tap(find.text('RF-DETR-M'));
    await tester.pumpAndSettle();
    expect(catalog.activated, ['rfdetr-m', 'r50-v5']);
    expect(find.text('That model could not be loaded. The previous model is still in use.'), findsOneWidget);
  });

  testWidgets('a count from a non-default model carries the banner on the result, in history and when shared',
      (tester) async {
    final history = MemoryHistory();
    final sharer = RecordingSharer();
    await tester.pumpWidget(
        RicePestApp(services: servicesWith(rf, FakeCatalog([r50, rf]), history: history, sharer: sharer)));
    await tester.pumpAndSettle();
    expect(find.text(banner), findsOneWidget);
    await tester.tap(find.text('Take a photo of the trap'));
    await tester.pumpAndSettle();
    expect(find.text(banner), findsOneWidget);
    expect(tester.widget<Text>(find.byKey(const Key('count-WSB'))).data, '2');
    expect(find.text('Please check this count against the photo'), findsNothing, reason: 'RF-DETR-M flags below 0.63 only');
    expect(history.entries.single.notValidated, isTrue);
    expect(history.entries.single.modelId, 'RF-DETR-M');
    await tester.tap(find.text('Share the counts'));
    await tester.pumpAndSettle();
    expect(sharer.text, startsWith(banner));
    for (final w in treatmentWords) {
      expect(sharer.text!.toLowerCase().contains(w), isFalse, reason: w);
    }
  });

  testWidgets('a count from the default model has no banner anywhere', (tester) async {
    final history = MemoryHistory();
    final sharer = RecordingSharer();
    await tester.pumpWidget(
        RicePestApp(services: servicesWith(r50, FakeCatalog([r50]), history: history, sharer: sharer)));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Take a photo of the trap'));
    await tester.pumpAndSettle();
    expect(find.text(banner), findsNothing);
    expect(find.text('Please check this count against the photo'), findsOneWidget, reason: 'r50-v5 flags below 0.64');
    await tester.tap(find.text('Share the counts'));
    await tester.pumpAndSettle();
    expect(sharer.text, startsWith('Trap photo'));
    expect(history.entries.single.notValidated, isFalse);
  });

  testWidgets('import: a verification failure is explained and nothing changes', (tester) async {
    final catalog = FakeCatalog([r50])
      ..importError = ModelImportFailed(ImportFailure.checksumMismatch, 'sha256');
    final files = FakeModelFiles(manifest: File('m.json'), model: File('m.onnx'));
    await tester.pumpWidget(RicePestApp(services: servicesWith(r50, catalog, files: files)));
    await tester.pumpAndSettle();
    await openSettings(tester);
    await tester.tap(find.text('Import a model from a file'));
    await tester.pumpAndSettle();
    expect(catalog.imported!.$1.path, 'm.onnx');
    expect(find.text('The model file does not match its manifest checksum. Nothing was imported.'), findsOneWidget);
    expect(catalog.activated, isEmpty);
    expect(find.text('D-FINE-L'), findsNothing);
  });

  testWidgets('import: each failure has its own message', (tester) async {
    const messages = {
      ImportFailure.manifestInvalid: 'The manifest file is not valid. Nothing was imported.',
      ImportFailure.sizeMismatch: 'The model file is not the size its manifest gives. Nothing was imported.',
      ImportFailure.shapeMismatch: 'The model\'s inputs or outputs do not fit this app. Nothing was imported.',
      ImportFailure.selfTestFailed: 'The model failed its self-test. Nothing was imported.',
      ImportFailure.alreadyInstalled: 'A model with this id is already installed. Nothing was imported.',
      ImportFailure.unreadable: 'The files could not be read. Nothing was imported.',
    };
    for (final e in messages.entries) {
      final catalog = FakeCatalog([r50])..importError = ModelImportFailed(e.key, 'x');
      await tester.pumpWidget(RicePestApp(
          key: UniqueKey(),
          services: servicesWith(r50, catalog, files: FakeModelFiles(manifest: File('m.json'), model: File('m.onnx')))));
      await tester.pumpAndSettle();
      await openSettings(tester);
      await tester.tap(find.text('Import a model from a file'));
      await tester.pumpAndSettle();
      expect(find.text(e.value), findsOneWidget, reason: e.key.name);
    }
  });

  testWidgets('import: a verified model appears in the list without becoming active', (tester) async {
    final catalog = FakeCatalog([r50]);
    final files = FakeModelFiles(manifest: File('m.json'), model: File('m.onnx'));
    await tester.pumpWidget(RicePestApp(services: servicesWith(r50, catalog, files: files)));
    await tester.pumpAndSettle();
    await openSettings(tester);
    await tester.tap(find.text('Import a model from a file'));
    await tester.pumpAndSettle();
    expect(find.text('Imported D-FINE-L. Tap it to use it.'), findsOneWidget);
    expect(find.text('D-FINE-L'), findsOneWidget);
    expect(catalog.activated, isEmpty);
  });

  testWidgets('import: cancelling either file picker does nothing', (tester) async {
    final catalog = FakeCatalog([r50]);
    await tester.pumpWidget(RicePestApp(
        services: servicesWith(r50, catalog, files: FakeModelFiles(manifest: File('m.json')))));
    await tester.pumpAndSettle();
    await openSettings(tester);
    await tester.tap(find.text('Import a model from a file'));
    await tester.pumpAndSettle();
    expect(catalog.imported, isNull);
  });

  testWidgets('deleting the active imported model asks first, then falls back to the default', (tester) async {
    final catalog = FakeCatalog([r50, rf]);
    var reloads = 0;
    await tester.pumpWidget(RicePestApp(
        services: servicesWith(rf, catalog),
        reload: () async {
          reloads++;
          return servicesWith(r50, catalog);
        }));
    await tester.pumpAndSettle();
    await openSettings(tester);
    await tester.tap(find.descendant(of: find.byKey(const Key('model-rfdetr-m')), matching: find.byIcon(Icons.delete_outline)));
    await tester.pumpAndSettle();
    expect(find.text('Delete RF-DETR-M from this phone?'), findsOneWidget);
    await tester.tap(find.text('Cancel'));
    await tester.pumpAndSettle();
    expect(catalog.deleted, isEmpty);
    await tester.tap(find.descendant(of: find.byKey(const Key('model-rfdetr-m')), matching: find.byIcon(Icons.delete_outline)));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Delete'));
    await tester.pumpAndSettle();
    expect(catalog.deleted, ['rfdetr-m']);
    expect(reloads, 1);
    expect(find.text(banner), findsNothing);
  });

  testWidgets('compare counts one photo with every installed model, one at a time, labelled as demo models',
      (tester) async {
    tallScreen(tester);
    final catalog = FakeCatalog([r50, rf, df]);
    final history = MemoryHistory();
    await tester.pumpWidget(RicePestApp(services: servicesWith(r50, catalog, history: history)));
    await tester.pumpAndSettle();
    await openSettings(tester);
    await tester.tap(find.text('Compare models on one photo'));
    await tester.pumpAndSettle();
    expect(find.text('Model comparison'), findsOneWidget);
    expect(find.textContaining('Comparison of demo models'), findsOneWidget);
    expect(find.text(banner), findsOneWidget);
    await tester.tap(find.text('Choose a photo'));
    await tester.pumpAndSettle();
    // The active model's detector is reused; the others are opened and closed one after another.
    expect(catalog.opened, ['rfdetr-m', 'dfine-l']);
    expect(catalog.closed, ['RF-DETR-M', 'D-FINE-L']);
    expect(catalog.maxOpen, 1);
    String cell(String id, String what) => tester.widget<Text>(find.byKey(Key('compare-$id-$what'))).data!;
    expect([cell('r50-v5', 'RBB'), cell('r50-v5', 'WSB')], ['2', '1']);
    expect([cell('rfdetr-m', 'RBB'), cell('rfdetr-m', 'WSB')], ['1', '2']);
    expect([cell('dfine-l', 'RBB'), cell('dfine-l', 'WSB')], ['0', '1']);
    expect(cell('r50-v5', 'flags'), 'Some insects were hard to recognise.');
    expect(cell('rfdetr-m', 'flags'), 'No review flags');
    expect(cell('dfine-l', 'flags'), 'No review flags');
    expect(cell('rfdetr-m', 'time'), matches(RegExp(r'^\d+\.\d s$')));
    expect(find.text('Not validated'), findsNWidgets(3));
    expect(history.entries, isEmpty, reason: 'comparisons are not saved');
  });

  testWidgets('a model that fails during the comparison is reported and the others still run', (tester) async {
    tallScreen(tester);
    final catalog = FakeCatalog([r50, model('broken', 'Broken'), df]);
    await tester.pumpWidget(RicePestApp(services: servicesWith(r50, catalog)));
    await tester.pumpAndSettle();
    await openSettings(tester);
    await tester.tap(find.text('Compare models on one photo'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Choose a photo'));
    await tester.pumpAndSettle();
    expect(find.text('This model could not count this photo.'), findsOneWidget);
    expect(tester.widget<Text>(find.byKey(const Key('compare-dfine-l-WSB'))).data, '1');
    expect(catalog.openNow, 0, reason: 'every opened model is closed, even after a failure');
  });

  testWidgets('Filipino locale shows the new strings in Filipino', (tester) async {
    await tester.pumpWidget(RicePestApp(services: servicesWith(rf, FakeCatalog([r50, rf])), locale: const Locale('fil')));
    await tester.pumpAndSettle();
    expect(find.textContaining('hindi pa napapatunayan'), findsOneWidget);
    await tester.tap(find.byTooltip('Mga setting'));
    await tester.pumpAndSettle();
    expect(find.text('Mag-import ng modelo mula sa file'), findsOneWidget);
  });

  testWidgets('the compare screen deletes its private photo copy when it closes', (tester) async {
    tallScreen(tester);
    final dir = Directory.systemTemp.createTempSync('compare-photo');
    addTearDown(() => dir.deleteSync(recursive: true));
    final copy = File('${dir.path}${Platform.pathSeparator}trap-1.jpg')..writeAsBytesSync([0]);
    await tester.pumpWidget(RicePestApp(
        services: servicesWith(r50, FakeCatalog([r50, rf]), photo: PhotoRef('trap-1.jpg', copy.path))));
    await tester.pumpAndSettle();
    await openSettings(tester);
    await tester.tap(find.text('Compare models on one photo'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Choose a photo'));
    await tester.pumpAndSettle();
    expect(copy.existsSync(), isTrue, reason: 'kept while its results are on screen');
    await tester.pageBack();
    await tester.pumpAndSettle();
    expect(copy.existsSync(), isFalse);
  });
}
