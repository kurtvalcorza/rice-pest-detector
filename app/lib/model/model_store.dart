// Pinned model install: download (or copy from a USB/LAN file)
// to a .part file, verify size and SHA-256, then rename into place. A failed install never
// replaces a good model. [fetchToFile] is the shared HTTP download, also used for published models.
import 'dart:async';
import 'dart:convert';
import 'dart:io';

import 'package:crypto/crypto.dart';
import 'package:http/http.dart' as http;

class ModelPin {
  const ModelPin(this.url, this.sha256, this.bytes, {this.threshold, this.label = '', this.kind = 'published'});

  factory ModelPin.fromJson(String json) {
    final d = jsonDecode(json) as Map<String, dynamic>;
    return ModelPin(d['url'] as String? ?? '', d['sha256'] as String? ?? '', (d['bytes'] as num?)?.toInt() ?? 0,
        threshold: (d['threshold'] as num?)?.toDouble(),
        label: d['label'] as String? ?? '',
        kind: d['kind'] as String? ?? 'published');
  }

  final String url;
  final String sha256;
  final int bytes;

  /// The model's own validation-chosen counting threshold; null means the contract default.
  final double? threshold;

  /// Shown as the model id on results; empty means the SHA-256 prefix.
  final String label;

  /// 'demo' (real weights, not field-validated: the Demo notice) or 'published' (passed the gates).
  final String kind;

  bool get isDemo => kind == 'demo';

  /// Empty: no model is pinned for download.
  bool get isSet => url.isNotEmpty && sha256.isNotEmpty && bytes > 0;
}

class ModelVerificationFailed implements Exception {
  ModelVerificationFailed(this.detail);
  final String detail;
  @override
  String toString() => 'Model file failed verification: $detail';
}

class ModelDownloadFailed implements Exception {
  ModelDownloadFailed(this.detail);
  final String detail;
  @override
  String toString() => 'Model download failed: $detail';
}

/// The user stopped a download.
class DownloadCancelled implements Exception {
  @override
  String toString() => 'Model download cancelled';
}

/// Lets the screen stop a download that is in progress.
class DownloadCancel {
  final _cancelled = Completer<void>();
  bool get isCancelled => _cancelled.isCompleted;
  Future<void> get whenCancelled => _cancelled.future;
  void cancel() {
    if (!_cancelled.isCompleted) _cancelled.complete();
  }
}

/// Bytes received so far and the total from the server's Content-Length (null when it sends none).
typedef DownloadProgress = void Function(int received, int? total);

/// Streams [url] into [out] (created or truncated), reporting progress after each chunk is written.
/// Throws [ModelDownloadFailed] on an HTTP error or broken connection, [ModelVerificationFailed] once more
/// than [maxBytes] arrive, and [DownloadCancelled] after [cancel]. On any failure [out] may hold a partial
/// file: the caller deletes it. Redirects are followed by the client.
Future<void> fetchToFile(http.Client client, Uri url, File out,
    {DownloadProgress? onProgress, DownloadCancel? cancel, int? maxBytes}) async {
  final http.StreamedResponse resp;
  try {
    resp = await client.send(http.AbortableRequest('GET', url, abortTrigger: cancel?.whenCancelled));
  } catch (e) {
    if (cancel?.isCancelled ?? false) throw DownloadCancelled();
    throw ModelDownloadFailed('$e');
  }
  if (cancel?.isCancelled ?? false) {
    unawaited(resp.stream.listen(null).cancel());
    throw DownloadCancelled();
  }
  if (resp.statusCode != 200) {
    unawaited(resp.stream.listen(null).cancel());
    throw ModelDownloadFailed('HTTP ${resp.statusCode}');
  }
  final total = resp.contentLength;
  await out.parent.create(recursive: true);
  final file = await out.open(mode: FileMode.write);
  final done = Completer<void>();
  var received = 0;
  var writing = Future<void>.value();
  late final StreamSubscription<List<int>> sub;
  void fail(Object error) {
    if (done.isCompleted) return;
    unawaited(sub.cancel());
    done.completeError(error);
  }

  sub = resp.stream.listen((chunk) {
    // Paused while the chunk is written, so a fast connection cannot fill memory.
    sub.pause();
    writing = file.writeFrom(chunk).then((_) {
      received += chunk.length;
      if (maxBytes != null && received > maxBytes) {
        fail(ModelVerificationFailed('more than the expected $maxBytes bytes'));
      } else if (!done.isCompleted) {
        onProgress?.call(received, total);
        sub.resume();
      }
    }, onError: (Object e) => fail(ModelDownloadFailed('$e')));
  }, onError: (Object e) {
    fail(e is http.RequestAbortedException ? DownloadCancelled() : ModelDownloadFailed('$e'));
  }, onDone: () {
    if (!done.isCompleted) done.complete();
  }, cancelOnError: true);
  unawaited(cancel?.whenCancelled.then((_) => fail(DownloadCancelled())));
  try {
    await done.future;
  } finally {
    await writing.catchError((_) {});
    await file.close();
  }
}

class ModelStore {
  ModelStore(this.dir, {this.client});

  final Directory dir;

  /// Injected in tests; a fresh client per download otherwise.
  final http.Client? client;

  File get modelFile => File('${dir.path}${Platform.pathSeparator}rice-pest.onnx');
  File get _part => File('${modelFile.path}.part');

  Future<bool> isInstalled(ModelPin pin) async {
    final f = modelFile;
    if (!pin.isSet || !await f.exists() || await f.length() != pin.bytes) return false;
    return (await sha256.bind(f.openRead()).first).toString() == pin.sha256;
  }

  Future<File> download(ModelPin pin) async {
    if (!pin.isSet) throw StateError('No model is published yet: the model pin is empty');
    final client = this.client ?? http.Client();
    try {
      try {
        await fetchToFile(client, Uri.parse(pin.url), _part, maxBytes: pin.bytes);
      } catch (_) {
        await _discardPart();
        rethrow;
      }
      return await _verifyAndInstall(pin);
    } finally {
      if (this.client == null) client.close();
    }
  }

  Future<File> installFromFile(File source, ModelPin pin) async {
    await dir.create(recursive: true);
    await source.copy(_part.path);
    return _verifyAndInstall(pin);
  }

  Future<File> _verifyAndInstall(ModelPin pin) async {
    final size = await _part.length();
    final digest = (await sha256.bind(_part.openRead()).first).toString();
    if (size != pin.bytes || digest != pin.sha256) {
      await _discardPart();
      throw ModelVerificationFailed('got $size bytes, sha256 $digest; expected ${pin.bytes}, ${pin.sha256}');
    }
    return _part.rename(modelFile.path);
  }

  Future<void> _discardPart() async {
    if (await _part.exists()) await _part.delete();
  }
}
