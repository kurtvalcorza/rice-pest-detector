import 'dart:convert';
import 'dart:io';

import 'package:crypto/crypto.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:rice_pest_app/model/model_store.dart';

void main() {
  late Directory dir;
  final payload = utf8.encode('pretend onnx bytes');
  final pin = ModelPin('https://example.invalid/rice-pest.onnx', sha256.convert(payload).toString(),
      payload.length);

  setUp(() => dir = Directory.systemTemp.createTempSync('model store '));
  tearDown(() => dir.deleteSync(recursive: true));

  test('pin parses the model_pin.json shape; an empty pin is not set', () {
    expect(ModelPin.fromJson('{"url": "", "sha256": "", "bytes": 0}').isSet, isFalse);
    final p = ModelPin.fromJson(jsonEncode({'url': pin.url, 'sha256': pin.sha256, 'bytes': pin.bytes}));
    expect([p.isSet, p.url, p.sha256, p.bytes], [true, pin.url, pin.sha256, pin.bytes]);
  });

  test('pin carries its own threshold, label and kind; defaults match the published contract', () {
    final demo = ModelPin.fromJson(jsonEncode({'url': pin.url, 'sha256': pin.sha256, 'bytes': pin.bytes,
        'threshold': 0.04, 'label': 'r50-v5-demo', 'kind': 'demo'}));
    expect([demo.threshold, demo.label, demo.isDemo], [0.04, 'r50-v5-demo', true]);
    final plain = ModelPin.fromJson(jsonEncode({'url': pin.url, 'sha256': pin.sha256, 'bytes': pin.bytes}));
    expect([plain.threshold, plain.label, plain.isDemo], [null, '', false]);
  });

  test('download streams to .part, verifies size and SHA-256, then installs', () async {
    final store = ModelStore(dir, client: MockClient((req) async {
      expect(req.url.toString(), pin.url);
      return http.Response.bytes(payload, 200);
    }));
    expect(await store.isInstalled(pin), isFalse);
    final f = await store.download(pin);
    expect(f.readAsBytesSync(), payload);
    expect(await store.isInstalled(pin), isTrue);
    expect(dir.listSync().where((e) => e.path.endsWith('.part')), isEmpty);
  });

  test('a corrupted download is rejected and nothing is installed', () async {
    final store = ModelStore(dir, client: MockClient((_) async => http.Response.bytes([...payload, 0], 200)));
    await expectLater(store.download(pin), throwsA(isA<ModelVerificationFailed>()));
    expect(store.modelFile.existsSync(), isFalse);
    expect(dir.listSync(), isEmpty);
  });

  test('HTTP errors are reported, not installed', () async {
    final store = ModelStore(dir, client: MockClient((_) async => http.Response('nope', 404)));
    await expectLater(store.download(pin), throwsA(isA<ModelDownloadFailed>()));
    expect(store.modelFile.existsSync(), isFalse);
  });

  test('an unset pin refuses to download', () async {
    final store = ModelStore(dir, client: MockClient((_) async => fail('must not call the network')));
    await expectLater(store.download(ModelPin('', '', 0)), throwsA(isA<StateError>()));
  });

  test('install from a local file (USB or LAN copy) verifies the same pin', () async {
    final src = File('${dir.path}${Platform.pathSeparator}copy.onnx')..writeAsBytesSync(payload);
    final store = ModelStore(dir);
    await store.installFromFile(src, pin);
    expect(await store.isInstalled(pin), isTrue);
    final bad = File('${dir.path}${Platform.pathSeparator}bad.onnx')..writeAsBytesSync([1, 2, 3]);
    await expectLater(store.installFromFile(bad, pin), throwsA(isA<ModelVerificationFailed>()));
    expect(await store.isInstalled(pin), isTrue, reason: 'a failed install keeps the good model');
  });

  test('a download that runs past the pinned size is stopped there', () async {
    var sent = 0;
    final store = ModelStore(dir, client: MockClient.streaming((_, _) async => http.StreamedResponse(
        Stream.fromIterable(List.generate(1000, (_) => List<int>.filled(1024, 0))).map((c) {
          sent += c.length;
          return c;
        }),
        200)));
    await expectLater(store.download(pin), throwsA(isA<ModelVerificationFailed>()));
    expect(sent, lessThan(100 * 1024), reason: 'stops near the ${pin.bytes} pinned bytes, not after 1 MB');
    expect(dir.listSync(), isEmpty);
  });
}
