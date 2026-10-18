// Settings → Download a model: the published models from the bundled catalogue, each with its facts and
// size and a Download button, or "Installed" / "In use" when its SHA-256 is already on the phone.
// Downloads show progress, can be cancelled, explain failures, and never make the model active.
import 'dart:async';
import 'dart:convert';
import 'dart:io';

import 'package:crypto/crypto.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:rice_pest_app/app/app.dart';
import 'package:rice_pest_app/model/model_manifest.dart';
import 'package:rice_pest_app/model/model_registry.dart';
import 'package:rice_pest_app/model/model_store.dart';
import 'package:rice_pest_app/model/published_models.dart';

import 'model_download_test.dart' show catalogAt;
import 'model_registry_test.dart' show manifestFor;
import 'models_ui_test.dart' show FakeCatalog, df, openSettings, r50, rf, servicesWith, tallScreen;

PublishedModel pub(String id, String label, String sha, {required int bytes, required String arch,
        int inputSize = 640, double threshold = 0.5, double reviewBelow = 0.68, double accuracy = 0.822}) =>
    PublishedModel(
        url: 'https://example.invalid/$id/model.onnx',
        manifest: ModelManifest(id: id, label: label, architecture: arch, baseModel: 'base', licence: 'Apache-2.0',
            inputSize: inputSize, threshold: threshold, reviewBelow: reviewBelow, sha256: sha, bytes: bytes,
            numClasses: 4, validation: ModelValidation(countAccuracy: accuracy, speciesMap50: 0.9, wsb30Mae: 9),
            validated: false));

final pR50 = pub('r50-v5', 'r50-v5', defaultModelSha256, bytes: 171744970, arch: 'RT-DETR (ResNet-50)',
    threshold: 0.48, reviewBelow: 0.64, accuracy: 0.834);
// Same SHA-256 as the installed RF-DETR-M in models_ui_test.dart.
final pRf = pub('rfdetr-m', 'RF-DETR-M', 'f' * 64, bytes: 121956743, arch: 'RF-DETR (medium)', inputSize: 576,
    threshold: 0.48, reviewBelow: 0.63, accuracy: 0.846);
final pDf = pub('dfine-l', 'D-FINE-L', 'd' * 64, bytes: 125213572, arch: 'D-FINE (large)');

Finder inRow(String id, Finder f) => find.descendant(of: find.byKey(Key('published-$id')), matching: f);

FakeCatalog catalogWithDownloads() => FakeCatalog([r50, rf])
  ..published = [pR50, pRf, pDf]
  ..downloadResult = df;

void main() {
  testWidgets('each published model is listed with its facts and size; installed ones say so', (tester) async {
    tallScreen(tester);
    final catalog = catalogWithDownloads();
    await tester.pumpWidget(RicePestApp(services: servicesWith(r50, catalog)));
    await tester.pumpAndSettle();
    await openSettings(tester);
    expect(find.text('Download a model'), findsOneWidget);
    expect(inRow('dfine-l', find.text('D-FINE-L')), findsOneWidget);
    expect(inRow('dfine-l', find.text('D-FINE (large) · 640 px · threshold 0.50 · count accuracy 0.822 (doing nothing: 0.474) · 125 MB')),
        findsOneWidget);
    expect(inRow('rfdetr-m', find.text('RF-DETR (medium) · 576 px · threshold 0.48 · count accuracy 0.846 (doing nothing: 0.474) · 122 MB')),
        findsOneWidget);
    expect(inRow('dfine-l', find.widgetWithText(FilledButton, 'Download')), findsOneWidget);
    expect(inRow('dfine-l', find.text('Installed')), findsNothing);
    // r50-v5 is installed and active; RF-DETR-M is installed (same SHA-256) but not in use.
    expect(inRow('r50-v5', find.text('Installed')), findsOneWidget);
    expect(inRow('r50-v5', find.text('In use')), findsOneWidget);
    expect(inRow('r50-v5', find.text('Download')), findsNothing);
    expect(inRow('rfdetr-m', find.text('Installed')), findsOneWidget);
    expect(inRow('rfdetr-m', find.text('In use')), findsNothing);
    expect(inRow('rfdetr-m', find.text('Download')), findsNothing);
    expect(catalog.downloaded, isEmpty, reason: 'nothing is fetched until the user taps Download');
  });

  testWidgets('a model whose id is installed but whose SHA-256 differs is not shown as installed', (tester) async {
    tallScreen(tester);
    final catalog = FakeCatalog([r50, rf])..published = [pub('rfdetr-m', 'RF-DETR-M', 'e' * 64, bytes: 1, arch: 'a')];
    await tester.pumpWidget(RicePestApp(services: servicesWith(r50, catalog)));
    await tester.pumpAndSettle();
    await openSettings(tester);
    expect(inRow('rfdetr-m', find.text('Installed')), findsNothing);
    expect(inRow('rfdetr-m', find.text('Download')), findsOneWidget);
  });

  testWidgets('a download shows its progress and can be cancelled', (tester) async {
    tallScreen(tester);
    final catalog = catalogWithDownloads()
      ..progressSteps = [(62606786, 125213572)]
      ..downloadGate = Completer<void>();
    await tester.pumpWidget(RicePestApp(services: servicesWith(r50, catalog)));
    await tester.pumpAndSettle();
    await openSettings(tester);
    await tester.tap(inRow('dfine-l', find.text('Download')));
    await tester.pump();
    expect(catalog.downloaded, ['dfine-l']);
    expect(inRow('dfine-l', find.text('Downloaded 62.6 of 125.2 MB')), findsOneWidget);
    expect(tester.widget<LinearProgressIndicator>(inRow('dfine-l', find.byType(LinearProgressIndicator))).value,
        closeTo(0.5, 1e-9));
    expect(find.text('Download'), findsNothing, reason: 'one download at a time');
    await tester.tap(inRow('dfine-l', find.text('Cancel download')));
    await tester.pumpAndSettle();
    expect(find.text('Download cancelled. Nothing was installed.'), findsOneWidget);
    expect(inRow('dfine-l', find.text('Download')), findsOneWidget);
    expect(find.byType(LinearProgressIndicator), findsNothing);
    expect(catalog.activated, isEmpty);
    expect(find.byKey(const Key('model-dfine-l')), findsNothing);
  });

  testWidgets('without a total size the progress bar is indeterminate', (tester) async {
    tallScreen(tester);
    final catalog = catalogWithDownloads()
      ..progressSteps = [(1000000, null)]
      ..downloadGate = Completer<void>();
    await tester.pumpWidget(RicePestApp(services: servicesWith(r50, catalog)));
    await tester.pumpAndSettle();
    await openSettings(tester);
    await tester.tap(inRow('dfine-l', find.text('Download')));
    await tester.pump();
    expect(inRow('dfine-l', find.text('Downloaded 1.0 MB')), findsOneWidget);
    expect(tester.widget<LinearProgressIndicator>(find.byType(LinearProgressIndicator)).value, isNull);
    catalog.downloadGate!.complete();
    await tester.pumpAndSettle();
  });

  testWidgets('a finished download is listed and installed but not made active', (tester) async {
    tallScreen(tester);
    final catalog = catalogWithDownloads();
    var reloads = 0;
    await tester.pumpWidget(RicePestApp(
        services: servicesWith(r50, catalog),
        reload: () async {
          reloads++;
          return servicesWith(r50, catalog);
        }));
    await tester.pumpAndSettle();
    await openSettings(tester);
    await tester.tap(inRow('dfine-l', find.text('Download')));
    await tester.pumpAndSettle();
    expect(find.text('Downloaded D-FINE-L. Tap it to use it.'), findsOneWidget);
    expect(find.byKey(const Key('model-dfine-l')), findsOneWidget);
    expect(catalog.activated, isEmpty);
    expect(reloads, 0);
    expect(find.descendant(of: find.byKey(const Key('model-dfine-l')), matching: find.text('Not validated')),
        findsOneWidget);
  });

  testWidgets('each download failure has its own message', (tester) async {
    tallScreen(tester);
    final messages = <Object, String>{
      ModelDownloadFailed('HTTP 500'):
          'The download failed. Check the connection and try again. Nothing was installed.',
      ModelImportFailed(ImportFailure.sizeMismatch, 'x'):
          'The downloaded file is not the expected size. Nothing was installed.',
      ModelImportFailed(ImportFailure.checksumMismatch, 'x'):
          'The downloaded file does not match its checksum. Nothing was installed.',
      ModelImportFailed(ImportFailure.shapeMismatch, 'x'): 'The downloaded model failed its checks. Nothing was installed.',
      ModelImportFailed(ImportFailure.selfTestFailed, 'x'):
          'The downloaded model failed its checks. Nothing was installed.',
      StateError('anything else'): 'The downloaded model failed its checks. Nothing was installed.',
    };
    for (final e in messages.entries) {
      final catalog = catalogWithDownloads()..downloadError = e.key;
      await tester.pumpWidget(RicePestApp(key: UniqueKey(), services: servicesWith(r50, catalog)));
      await tester.pumpAndSettle();
      await openSettings(tester);
      await tester.tap(inRow('dfine-l', find.text('Download')));
      await tester.pumpAndSettle();
      expect(find.text(e.value), findsOneWidget, reason: '${e.key}');
      expect(catalog.activated, isEmpty);
      expect(inRow('dfine-l', find.text('Download')), findsOneWidget);
    }
  });

  testWidgets('Filipino locale shows the download section in Filipino', (tester) async {
    tallScreen(tester);
    await tester.pumpWidget(
        RicePestApp(services: servicesWith(r50, catalogWithDownloads()), locale: const Locale('fil')));
    await tester.pumpAndSettle();
    await tester.tap(find.byTooltip('Mga setting'));
    await tester.pumpAndSettle();
    expect(find.text('Mag-download ng modelo'), findsOneWidget);
    expect(inRow('dfine-l', find.text('I-download')), findsOneWidget);
    expect(inRow('rfdetr-m', find.text('Naka-install')), findsOneWidget);
  });

  group('with the real catalog over a fake HTTP client', () {
    late Directory root;
    final payload = utf8.encode('pretend onnx bytes for the settings screen');
    setUp(() => root = Directory.systemTemp.createTempSync('settings download '));
    tearDown(() => root.deleteSync(recursive: true));

    /// Real file I/O needs real time: alternate real waits and frames until [done].
    Future<void> settle(WidgetTester tester, bool Function() done) async {
      for (var i = 0; i < 400 && !done(); i++) {
        await tester.runAsync(() => Future<void>.delayed(const Duration(milliseconds: 5)));
        await tester.pump();
      }
    }

    PublishedModel entry({String? sha}) => PublishedModel(
        url: 'https://example.invalid/model.onnx', manifest: ModelManifest.fromJson(manifestFor(payload, sha: sha)));

    testWidgets('a download installs the model and its row then says Installed', (tester) async {
      tallScreen(tester);
      final client = MockClient((req) async => http.Response.bytes(payload, 200));
      final catalog = catalogAt(root, client, [entry()]);
      await tester.pumpWidget(RicePestApp(services: servicesWith(r50, catalog)));
      await tester.pumpAndSettle();
      await openSettings(tester);
      await tester.tap(inRow('rfdetr-m', find.text('Download')));
      await settle(tester, () => inRow('rfdetr-m', find.text('Installed')).evaluate().isNotEmpty);
      expect(inRow('rfdetr-m', find.text('Installed')), findsOneWidget);
      expect(find.byKey(const Key('model-rfdetr-m')), findsOneWidget);
      expect(find.text('Downloaded RFDETR-M. Tap it to use it.'), findsOneWidget);
      await tester.runAsync(() async => expect(await ModelRegistry(Directory('${root.path}${Platform.pathSeparator}models')).activeId(), isNull));
    });

    testWidgets('a checksum mismatch is explained and nothing is installed', (tester) async {
      tallScreen(tester);
      final client = MockClient((req) async => http.Response.bytes(payload, 200));
      final catalog = catalogAt(root, client, [entry(sha: sha256.convert([1]).toString())]);
      await tester.pumpWidget(RicePestApp(services: servicesWith(r50, catalog)));
      await tester.pumpAndSettle();
      await openSettings(tester);
      await tester.tap(inRow('rfdetr-m', find.text('Download')));
      const message = 'The downloaded file does not match its checksum. Nothing was installed.';
      await settle(tester, () => find.text(message).evaluate().isNotEmpty);
      expect(find.text(message), findsOneWidget);
      await settle(tester, () => inRow('rfdetr-m', find.text('Download')).evaluate().isNotEmpty);
      expect(inRow('rfdetr-m', find.text('Download')), findsOneWidget);
      final files = await tester.runAsync(() async => root.list(recursive: true).where((e) => e is File).toList());
      expect(files, isEmpty, reason: 'no .part or staged files');
    });
  });
}
