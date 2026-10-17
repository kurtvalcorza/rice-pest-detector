// Downloading a published model in Settings: the file is streamed to a .part file, then installed through
// the same registry path as a file import (size, SHA-256, session check). Any failure or a cancel leaves
// no files behind and does not change the active model; a downloaded model is never made active.
import 'dart:async';
import 'dart:convert';
import 'dart:io';

import 'package:crypto/crypto.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:rice_pest_app/app/model_catalog.dart';
import 'package:rice_pest_app/inference/detector.dart';
import 'package:rice_pest_app/model/model_manifest.dart';
import 'package:rice_pest_app/model/model_registry.dart';
import 'package:rice_pest_app/model/model_store.dart';
import 'package:rice_pest_app/model/published_models.dart';

import 'model_registry_test.dart' show manifestFor, passes;

String sep = Platform.pathSeparator;
const url = 'https://example.invalid/rfdetr-m/model.onnx';

PublishedModel publishedFor(List<int> payload, {String? sha, int? bytes}) =>
    PublishedModel(url: url, manifest: ModelManifest.fromJson(manifestFor(payload, sha: sha, bytes: bytes)));

/// A local catalog over a temp registry; the legacy pin and demo model are absent.
LocalModelCatalog catalogAt(Directory root, http.Client client, List<PublishedModel> published,
        {ModelCheck check = passes}) =>
    LocalModelCatalog(
        registry: ModelRegistry(Directory('${root.path}${sep}models')),
        pin: const ModelPin('', '', 0),
        store: ModelStore(Directory('${root.path}${sep}model')),
        demoStore: ModelStore(Directory('${root.path}${sep}demo')),
        demoMeta: File('${root.path}${sep}demo${sep}demo.json'),
        load: (_) async => throw UnimplementedError(),
        unload: (Detector _) async {},
        check: check,
        published: published,
        client: client);

void main() {
  late Directory root;
  final payload = utf8.encode('pretend onnx bytes, long enough to arrive in more than one chunk');

  setUp(() => root = Directory.systemTemp.createTempSync('download '));
  tearDown(() => root.deleteSync(recursive: true));

  ModelRegistry registry() => ModelRegistry(Directory('${root.path}${sep}models'));

  /// Everything under app storage, so a stray .part file anywhere is caught.
  List<String> leftovers() => root.existsSync()
      ? root.listSync(recursive: true).whereType<File>().map((f) => f.path.substring(root.path.length + 1)).toList()
      : [];

  MockClient serving(List<int> body, {int status = 200}) => MockClient((req) async {
        expect(req.url.toString(), url);
        return http.Response.bytes(body, status);
      });

  test('a published model downloads, installs, is listed, and is not made active', () async {
    await registry().setActive('r50-v5');
    final progress = <(int, int?)>[];
    final c = catalogAt(root, serving(payload), [publishedFor(payload)]);
    final m = await c.download(c.published.single, onProgress: (r, t) => progress.add((r, t)));
    expect([m.id, m.label, m.source], ['rfdetr-m', 'RFDETR-M', ModelSource.registry]);
    expect(File(m.path).readAsBytesSync(), payload);
    expect((await c.list()).map((e) => e.id), ['rfdetr-m']);
    expect(await registry().activeId(), 'r50-v5');
    expect(progress.last, (payload.length, payload.length));
    expect(leftovers().where((p) => p.endsWith('.part') || p.contains('.import-')), isEmpty);
  });

  test('progress has no total when the server sends no length', () async {
    final client = MockClient.streaming((req, _) async =>
        http.StreamedResponse(Stream.fromIterable([payload.sublist(0, 10), payload.sublist(10)]), 200));
    final progress = <(int, int?)>[];
    final c = catalogAt(root, client, [publishedFor(payload)]);
    await c.download(c.published.single, onProgress: (r, t) => progress.add((r, t)));
    expect(progress, [(10, null), (payload.length, null)]);
  });

  Future<void> rollsBack(LocalModelCatalog c, Matcher error) async {
    await registry().setActive('r50-v5');
    await expectLater(c.download(c.published.single), throwsA(error));
    expect(leftovers(), ['models${sep}active.json'], reason: 'no .part, staging or model files are left');
    expect(await registry().activeId(), 'r50-v5');
    expect(await c.list(), isEmpty);
  }

  Matcher importFailure(ImportFailure reason) => isA<ModelImportFailed>().having((e) => e.reason, 'reason', reason);

  test('a file of the wrong size (shorter) rolls back', () async {
    await rollsBack(catalogAt(root, serving(payload.sublist(1)), [publishedFor(payload)]),
        importFailure(ImportFailure.sizeMismatch));
  });

  test('a file larger than the catalogue says is stopped and rolled back', () async {
    await rollsBack(catalogAt(root, serving([...payload, 0, 0]), [publishedFor(payload)]),
        importFailure(ImportFailure.sizeMismatch));
  });

  test('a SHA-256 mismatch rolls back', () async {
    final other = [...payload.reversed];
    await rollsBack(catalogAt(root, serving(other), [publishedFor(payload)]),
        importFailure(ImportFailure.checksumMismatch));
  });

  test('a failed self-test rolls back', () async {
    await rollsBack(
        catalogAt(root, serving(payload), [publishedFor(payload)],
            check: (_, _) async => throw ModelImportFailed(ImportFailure.selfTestFailed, 'non-finite')),
        importFailure(ImportFailure.selfTestFailed));
  });

  test('wrong input/output shapes roll back', () async {
    await rollsBack(
        catalogAt(root, serving(payload), [publishedFor(payload)],
            check: (_, _) async => throw ModelImportFailed(ImportFailure.shapeMismatch, '576')),
        importFailure(ImportFailure.shapeMismatch));
  });

  test('the session check sees the downloaded file in the registry, not the .part file', () async {
    String? seen;
    final c = catalogAt(root, serving(payload), [publishedFor(payload)], check: (p, _) async => seen = p);
    await c.download(c.published.single);
    expect(seen, isNot(endsWith('.part')));
    expect(seen, contains('models'));
  });

  test('HTTP errors and broken connections roll back as network failures', () async {
    await rollsBack(catalogAt(root, serving([], status: 404), [publishedFor(payload)]), isA<ModelDownloadFailed>());
    Stream<List<int>> resetAfterTenBytes() async* {
      yield payload.sublist(0, 10);
      throw const SocketException('reset');
    }

    final broken = MockClient.streaming(
        (req, _) async => http.StreamedResponse(resetAfterTenBytes(), 200, contentLength: payload.length));
    await rollsBack(catalogAt(root, broken, [publishedFor(payload)]), isA<ModelDownloadFailed>());
    final unreachable = MockClient((_) async => throw const SocketException('no route'));
    await rollsBack(catalogAt(root, unreachable, [publishedFor(payload)]), isA<ModelDownloadFailed>());
  });

  test('cancelling mid-download stops it and cleans up', () async {
    final body = StreamController<List<int>>();
    final client = MockClient.streaming(
        (req, _) async => http.StreamedResponse(body.stream, 200, contentLength: payload.length));
    final cancel = DownloadCancel();
    final c = catalogAt(root, client, [publishedFor(payload)]);
    await registry().setActive('r50-v5');
    final firstChunk = Completer<void>();
    final run = c.download(c.published.single, cancel: cancel, onProgress: (_, _) {
      if (!firstChunk.isCompleted) firstChunk.complete();
    });
    body.add(payload.sublist(0, 10));
    await firstChunk.future;
    expect(leftovers().where((p) => p.endsWith('.part')), hasLength(1), reason: 'streams to a staging .part file');
    cancel.cancel();
    await expectLater(run, throwsA(isA<DownloadCancelled>()));
    expect(body.hasListener, isFalse, reason: 'the response stream is no longer read');
    expect(leftovers(), ['models${sep}active.json']);
    expect(await registry().activeId(), 'r50-v5');
    await body.close();
  });

  test('a model already in the registry is not downloaded again', () async {
    final c = catalogAt(root, serving(payload), [publishedFor(payload)]);
    await c.download(c.published.single);
    final again = catalogAt(root, MockClient((_) async => fail('must not call the network')), [publishedFor(payload)]);
    await expectLater(again.download(again.published.single), throwsA(importFailure(ImportFailure.alreadyInstalled)));
    expect(File((await again.list()).single.path).readAsBytesSync(), payload);
  });

  test('the downloaded copy is the one the registry verifies (SHA-256 recomputed from disk)', () async {
    final c = catalogAt(root, serving(payload), [publishedFor(payload)]);
    final m = await c.download(c.published.single);
    expect(sha256.convert(File(m.path).readAsBytesSync()).toString(), m.sha256);
  });
}
