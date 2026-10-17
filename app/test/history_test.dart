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
