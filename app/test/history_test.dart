import 'dart:convert';
import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:rice_pest_app/storage/history.dart';

HistoryEntry entry(String id, DateTime at, {String? photo}) => HistoryEntry(
    id: id, takenAt: at, photoPath: photo, counts: {'RBB': 3, 'WSB': 0}, reasons: ['lowConfidence'],
    threshold: 0.5, modelId: 'test:abc');

void main() {
  late Directory dir;
  setUp(() => dir = Directory.systemTemp.createTempSync('history '));
  tearDown(() => dir.deleteSync(recursive: true));

  test('entries round-trip and load newest first', () async {
    final store = HistoryStore(dir);
    expect(await store.load(), isEmpty);
    await store.add(entry('a', DateTime.utc(2026, 10, 1)));
    await store.add(entry('b', DateTime.utc(2026, 10, 3)));
    final got = await HistoryStore(dir).load(); // a fresh instance reads from disk
    expect(got.map((e) => e.id), ['b', 'a']);
    expect(got.first.counts, {'RBB': 3, 'WSB': 0});
    expect(got.first.reasons, ['lowConfidence']);
    expect([got.first.threshold, got.first.modelId], [0.5, 'test:abc']);
    expect(got.first.takenAt, DateTime.utc(2026, 10, 3));
  });

  test('delete removes the entry and its photo file', () async {
    final photo = File('${dir.path}${Platform.pathSeparator}p.jpg')..writeAsBytesSync([1]);
    final store = HistoryStore(dir);
    await store.add(entry('a', DateTime.utc(2026, 10, 1), photo: photo.path));
    await store.delete('a');
    expect(await store.load(), isEmpty);
    expect(photo.existsSync(), isFalse);
  });

  test('a corrupted history file is set aside, not fatal', () async {
    File('${dir.path}${Platform.pathSeparator}history.json').writeAsStringSync('{not json');
    final store = HistoryStore(dir);
    expect(await store.load(), isEmpty);
    expect(dir.listSync().map((e) => e.uri.pathSegments.last), contains('history.json.corrupt'));
    await store.add(entry('a', DateTime.utc(2026, 10, 1)));
    expect((await store.load()).single.id, 'a');
  });

  test('writes are atomic: no temp file left behind', () async {
    await HistoryStore(dir).add(entry('a', DateTime.utc(2026, 10, 1)));
    expect(dir.listSync().where((e) => e.path.endsWith('.tmp')), isEmpty);
  });

  test('two models with one label are stored apart: label, registry id and SHA-256 round-trip', () async {
    final store = HistoryStore(dir);
    HistoryEntry by(String id, String registryId, String sha) => HistoryEntry(id: id, takenAt: DateTime.utc(2026, 10, 2),
        photoPath: null, counts: {'RBB': 1, 'WSB': 0}, reasons: [], threshold: 0.48, modelId: 'RF-DETR-M',
        modelRegistryId: registryId, modelSha256: sha);
    await store.add(by('x', 'rfdetr-m', '1' * 64));
    await store.add(by('y', 'rfdetr-m-2', '2' * 64));
    final got = {for (final e in await HistoryStore(dir).load()) e.id: e};
    expect([got['x']!.modelId, got['x']!.modelRegistryId, got['x']!.modelSha256], ['RF-DETR-M', 'rfdetr-m', '1' * 64]);
    expect([got['y']!.modelId, got['y']!.modelRegistryId, got['y']!.modelSha256], ['RF-DETR-M', 'rfdetr-m-2', '2' * 64]);
    expect([got['x']!.modelDisplay, got['y']!.modelDisplay], ['RF-DETR-M (111111111111)', 'RF-DETR-M (222222222222)']);
  });

  test('a history file from before model identity was recorded loads with the id and hash unknown', () async {
    File('${dir.path}${Platform.pathSeparator}history.json').writeAsStringSync(jsonEncode([
      {'id': 'o', 'takenAt': '2026-10-01T00:00:00.000Z', 'photoPath': null, 'counts': {'RBB': 2, 'WSB': 1},
        'reasons': [], 'threshold': 0.48, 'modelId': 'r50-v5-demo', 'notValidated': true},
    ]));
    final store = HistoryStore(dir);
    final old = (await store.load()).single;
    expect([old.modelId, old.modelSha256, old.modelRegistryId, old.modelDisplay],
        ['r50-v5-demo', null, null, 'r50-v5-demo']);
    expect(dir.listSync().map((e) => e.uri.pathSegments.last), isNot(contains('history.json.corrupt')));
    await store.add(entry('n', DateTime.utc(2026, 10, 3))); // rewriting keeps the old entry as it was
    final again = (await HistoryStore(dir).load()).last;
    expect([again.id, again.modelId, again.modelSha256, again.modelRegistryId], ['o', 'r50-v5-demo', null, null]);
  });

  test('entries record whether the model was not validated; old entries read as validated-default', () async {
    final store = HistoryStore(dir);
    await store.add(HistoryEntry(id: 'n', takenAt: DateTime.utc(2026, 10, 2), photoPath: null,
        counts: {'RBB': 1, 'WSB': 0}, reasons: [], threshold: 0.48, modelId: 'RF-DETR-M', notValidated: true));
    expect((await HistoryStore(dir).load()).single.notValidated, isTrue);
    final old = HistoryEntry.fromJson({'id': 'o', 'takenAt': '2026-10-01T00:00:00.000Z', 'photoPath': null,
        'counts': {'RBB': 0, 'WSB': 0}, 'reasons': [], 'threshold': 0.48, 'modelId': 'r50-v5-demo'});
    expect(old.notValidated, isFalse);
  });
}
