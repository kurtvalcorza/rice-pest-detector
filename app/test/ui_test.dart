import 'dart:async';
import 'dart:convert';
import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:rice_pest_app/app/app.dart';
import 'package:rice_pest_app/app/services.dart';
import 'package:rice_pest_app/inference/detector.dart';
import 'package:rice_pest_app/inference/preprocess.dart';
import 'package:rice_pest_app/model/model_store.dart';
import 'package:rice_pest_app/storage/history.dart';

import 'l10n_test.dart' show treatmentWords;

final fixtures = jsonEncode({
  'onnx_sha256': 'abc123',
  'images': [
    {
      'file': 'trap-1.jpg', 'width': 640, 'height': 640,
      'detections': [
        {'class_id': 0, 'score': 0.91, 'box': [1, 2, 3, 4]},
        {'class_id': 1, 'score': 0.055, 'box': [1, 2, 3, 4]}, // counted, but low confidence (< 0.64)
        {'class_id': 2, 'score': 0.04, 'box': [1, 2, 3, 4]}, // exactly at threshold: counted
        {'class_id': 3, 'score': 0.03, 'box': [1, 2, 3, 4]}, // below threshold
      ],
    },
  ],
});

class FakePhotos implements PhotoSource {
  FakePhotos(this.next);
  PhotoRef? next;

  /// When set, the picker stays open until the test completes it.
  Completer<PhotoRef?>? pending;
  final discarded = <String?>[];
  @override
  Future<PhotoRef?> camera() async => pending == null ? next : pending!.future;
  @override
  Future<PhotoRef?> gallery() async => pending == null ? next : pending!.future;
  @override
  Future<void> discard(PhotoRef photo) async {
    discarded.add(photo.path);
    // Synchronous: real async file IO does not complete inside testWidgets' fake clock.
    final path = photo.path;
    if (path != null && File(path).existsSync()) File(path).deleteSync();
  }
}

class RecordingSharer implements Sharer {
  String? text;
  String? photoPath;
  @override
  Future<void> share(String text, {String? photoPath}) async {
    this.text = text;
    this.photoPath = photoPath;
  }
}

class MemoryHistory implements History {
  final entries = <HistoryEntry>[];
  @override
  Future<List<HistoryEntry>> load() async => [...entries]..sort((a, b) => b.takenAt.compareTo(a.takenAt));
  @override
  Future<void> add(HistoryEntry e) async => entries.add(e);
  @override
  Future<void> delete(String id) async => entries.removeWhere((e) => e.id == id);
}

class TooSmallDetector implements Detector {
  @override
  String get modelId => 'test';
  @override
  Future<List<Never>> detect(PhotoRef photo) async => throw PhotoTooSmall(10, 10);
}

/// Fails the way a broken model session would.
class BrokenDetector implements Detector {
  @override
  String get modelId => 'broken';
  @override
  Future<List<Never>> detect(PhotoRef photo) async => throw StateError('session closed');
}

/// Holds every count until [gate] completes, so a test can act while the count is running.
class GateDetector implements Detector {
  final gate = Completer<void>();
  @override
  String get modelId => 'gate';
  @override
  Future<List<Never>> detect(PhotoRef photo) async {
    await gate.future;
    return const [];
  }
}

/// A private photo copy in a temporary folder, removed after the test.
File tempPhoto() {
  final dir = Directory.systemTemp.createTempSync('home-photo');
  addTearDown(() => dir.deleteSync(recursive: true));
  return File('${dir.path}${Platform.pathSeparator}trap-1.jpg')..writeAsBytesSync([0]);
}

Finder get settingsButton => find.widgetWithIcon(IconButton, Icons.settings_outlined);

AppServices services({Detector? detector, MemoryHistory? history, RecordingSharer? sharer, PhotoRef? photo,
        FakePhotos? photos, ModelMode mode = ModelMode.published, double threshold = 0.04}) =>
    AppServices(
      detector: mode == ModelMode.none ? null : detector ?? FakeDetector.fromJson(fixtures),
      history: history ?? MemoryHistory(),
      photos: photos ?? FakePhotos(photo ?? const PhotoRef('trap-1.jpg', '/photos/trap-1.jpg')),
      sharer: sharer ?? RecordingSharer(),
      mode: mode,
      threshold: threshold,
      now: () => DateTime(2026, 10, 16, 9, 30),
      newId: () => 'id-1',
    );

void main() {
  downloadTests();
  photoLifecycleTests();
  testWidgets('home shows the model notice and the photo buttons', (tester) async {
    await tester.pumpWidget(RicePestApp(services: services()));
    await tester.pumpAndSettle();
    expect(find.textContaining('Experimental model'), findsOneWidget);
    expect(find.text('Take a photo of the trap'), findsOneWidget);
    expect(find.text('Choose a photo'), findsOneWidget);
    expect(find.text('No counts yet.'), findsOneWidget);
  });

  testWidgets('with no model installed the app says so and cannot count', (tester) async {
    final history = MemoryHistory();
    await tester.pumpWidget(RicePestApp(services: services(history: history, mode: ModelMode.none)));
    await tester.pumpAndSettle();
    expect(find.textContaining('No model is installed'), findsOneWidget);
    expect(find.textContaining('Experimental model'), findsNothing);
    final camera = tester.widget<ButtonStyleButton>(
        find.ancestor(of: find.text('Take a photo of the trap'), matching: find.bySubtype<ButtonStyleButton>()));
    final gallery = tester.widget<ButtonStyleButton>(
        find.ancestor(of: find.text('Choose a photo'), matching: find.bySubtype<ButtonStyleButton>()));
    expect([camera.onPressed, gallery.onPressed], [null, null]);
    await tester.tap(find.text('Take a photo of the trap'));
    await tester.pumpAndSettle();
    expect(history.entries, isEmpty);
  });

  testWidgets('a photo is counted, flagged for review, saved, and shown', (tester) async {
    final history = MemoryHistory();
    await tester.pumpWidget(RicePestApp(services: services(history: history)));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Take a photo of the trap'));
    await tester.pumpAndSettle();
    expect(find.text('Rice black bug (atangya)'), findsOneWidget);
    expect(find.byKey(const Key('count-RBB')), findsOneWidget);
    expect(tester.widget<Text>(find.byKey(const Key('count-RBB'))).data, '2');
    expect(tester.widget<Text>(find.byKey(const Key('count-WSB'))).data, '1');
    expect(find.text('Please check this count against the photo'), findsOneWidget);
    expect(find.text('Some insects were hard to recognise.'), findsOneWidget);
    expect(find.text('Model fake:abc123 · threshold 0.04'), findsOneWidget);
    expect(find.textContaining('Experimental model'), findsOneWidget);
    expect(history.entries.single.counts, {'RBB': 2, 'WSB': 1});
    expect(history.entries.single.photoPath, '/photos/trap-1.jpg');
  });

  testWidgets('share sends a reviewable summary and the photo, with no treatment advice', (tester) async {
    final sharer = RecordingSharer();
    await tester.pumpWidget(RicePestApp(services: services(sharer: sharer)));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Take a photo of the trap'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Share the counts'));
    await tester.pumpAndSettle();
    expect(sharer.text, 'Trap photo 2026-10-16 09:30: rice black bug 2, white stemborer 1. '
        'Model fake:abc123, threshold 0.04. Counts are estimates; please review.');
    expect(sharer.photoPath, '/photos/trap-1.jpg');
    for (final w in treatmentWords) {
      expect(sharer.text!.toLowerCase().contains(w), isFalse, reason: w);
    }
  });

  testWidgets('Filipino locale shows Filipino text', (tester) async {
    await tester.pumpWidget(RicePestApp(services: services(), locale: const Locale('fil')));
    await tester.pumpAndSettle();
    expect(find.text('Kunan ng litrato ang bitag'), findsOneWidget);
    expect(find.text('Wala pang bilang.'), findsOneWidget);
  });

  testWidgets('a photo that is too small explains itself and saves nothing', (tester) async {
    final history = MemoryHistory();
    await tester.pumpWidget(RicePestApp(services: services(detector: TooSmallDetector(), history: history)));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Take a photo of the trap'));
    await tester.pumpAndSettle();
    expect(find.text('This photo is too small. Take a closer photo of the trap.'), findsOneWidget);
    expect(history.entries, isEmpty);
  });

  testWidgets('past counts are listed newest first and open again', (tester) async {
    final history = MemoryHistory();
    await tester.pumpWidget(RicePestApp(services: services(history: history)));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Take a photo of the trap'));
    await tester.pumpAndSettle();
    await tester.pageBack();
    await tester.pumpAndSettle();
    expect(find.text('2026-10-16 09:30'), findsOneWidget);
    await tester.tap(find.text('2026-10-16 09:30'));
    await tester.pumpAndSettle();
    expect(tester.widget<Text>(find.byKey(const Key('count-RBB'))).data, '2');
  });

  testWidgets('demo mode uses the real-weights notice and the demo threshold', (tester) async {
    final history = MemoryHistory();
    await tester.pumpWidget(RicePestApp(
        services: services(history: history, mode: ModelMode.demo, threshold: 0.03)));
    await tester.pumpAndSettle();
    expect(find.textContaining('No model is installed'), findsNothing);
    expect(find.textContaining('Demo'), findsOneWidget);
    await tester.tap(find.text('Take a photo of the trap'));
    await tester.pumpAndSettle();
    expect(tester.widget<Text>(find.byKey(const Key('count-WSB'))).data, '2'); // 0.04 and 0.03 both counted
    expect(find.text('Model fake:abc123 · threshold 0.03'), findsOneWidget);
    expect(history.entries.single.threshold, 0.03);
  });
}
AppServices noModelWithDownload({required Future<void> Function(DownloadCancel cancel) run}) => AppServices(
      history: MemoryHistory(),
      photos: FakePhotos(const PhotoRef('trap-1.jpg', '/photos/trap-1.jpg')),
      sharer: RecordingSharer(),
      mode: ModelMode.none,
      download: ModelDownload(bytes: 171744970, label: 'r50-v5-demo', run: run),
    );

void downloadTests() {
  testWidgets('with a pinned model not yet installed, the app offers the download and its size', (tester) async {
    await tester.pumpWidget(RicePestApp(services: noModelWithDownload(run: (_) async {})));
    await tester.pumpAndSettle();
    expect(find.textContaining('No model is installed'), findsOneWidget);
    expect(find.text('Download the model (172 MB)'), findsOneWidget);
  });

  testWidgets('a successful download reloads the app into the pin\'s mode and threshold', (tester) async {
    var ran = false;
    await tester.pumpWidget(RicePestApp(
      services: noModelWithDownload(run: (_) async => ran = true),
      reload: () async => services(mode: ModelMode.demo, threshold: 0.04),
    ));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Download the model (172 MB)'));
    await tester.pumpAndSettle();
    expect(ran, isTrue);
    expect(find.textContaining('Demo'), findsOneWidget);
    await tester.tap(find.text('Take a photo of the trap'));
    await tester.pumpAndSettle();
    expect(find.text('Model fake:abc123 · threshold 0.04'), findsOneWidget);
  });

  testWidgets('a failed or rejected download keeps the app in no-model mode and says so', (tester) async {
    await tester.pumpWidget(RicePestApp(
      services: noModelWithDownload(run: (_) async => throw ModelVerificationFailed('sha256 mismatch')),
      reload: () async => fail('must not reload after a failed download'),
    ));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Download the model (172 MB)'));
    await tester.pumpAndSettle();
    expect(find.text('The model download failed. Check the connection and try again.'), findsOneWidget);
    expect(find.textContaining('No model is installed'), findsOneWidget);
  });

  testWidgets('the home download can be cancelled, and nothing is installed', (tester) async {
    await tester.pumpWidget(RicePestApp(
      services: noModelWithDownload(run: (cancel) async {
        await cancel.whenCancelled;
        throw DownloadCancelled();
      }),
      reload: () async => fail('must not reload after a cancelled download'),
    ));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Download the model (172 MB)'));
    await tester.pump();
    expect(find.text('Downloading the model…'), findsOneWidget);
    await tester.tap(find.text('Cancel download'));
    await tester.pumpAndSettle();
    expect(find.text('Download cancelled. Nothing was installed.'), findsOneWidget);
    expect(find.text('Download the model (172 MB)'), findsOneWidget);
  });

  testWidgets('leaving the home screen stops its download', (tester) async {
    var stopped = false;
    await tester.pumpWidget(RicePestApp(services: noModelWithDownload(run: (cancel) async {
      await cancel.whenCancelled;
      stopped = true;
      throw DownloadCancelled();
    })));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Download the model (172 MB)'));
    await tester.pump();
    await tester.pumpWidget(const SizedBox());
    await tester.pump();
    expect(stopped, isTrue);
  });
}

void photoLifecycleTests() {
  testWidgets('a counted photo is kept for its history entry', (tester) async {
    final copy = tempPhoto();
    final photos = FakePhotos(PhotoRef('trap-1.jpg', copy.path));
    final history = MemoryHistory();
    await tester.pumpWidget(RicePestApp(services: services(history: history, photos: photos)));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Take a photo of the trap'));
    await tester.pumpAndSettle();
    expect(history.entries.single.photoPath, copy.path);
    expect(photos.discarded, isEmpty);
    expect(copy.existsSync(), isTrue);
  });

  testWidgets('a photo the model rejects is not kept: its private copy is deleted', (tester) async {
    final copy = tempPhoto();
    final history = MemoryHistory();
    await tester.pumpWidget(RicePestApp(services: services(
        detector: TooSmallDetector(), history: history, photo: PhotoRef('trap-1.jpg', copy.path))));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Take a photo of the trap'));
    await tester.pumpAndSettle();
    expect(find.textContaining('too small'), findsOneWidget);
    expect(history.entries, isEmpty);
    expect(copy.existsSync(), isFalse);
  });

  testWidgets('a count that fails for another reason says so and keeps nothing', (tester) async {
    final copy = tempPhoto();
    final history = MemoryHistory();
    await tester.pumpWidget(RicePestApp(services: services(
        detector: BrokenDetector(), history: history, photo: PhotoRef('trap-1.jpg', copy.path))));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Take a photo of the trap'));
    await tester.pumpAndSettle();
    expect(find.text('This photo could not be counted, and nothing was saved. Try again.'), findsOneWidget);
    expect(history.entries, isEmpty);
    expect(copy.existsSync(), isFalse);
    expect(find.text('Take a photo of the trap'), findsOneWidget, reason: 'the app is ready for the next photo');
  });

  testWidgets('a photo that arrives after the home screen has gone is deleted', (tester) async {
    final copy = tempPhoto();
    final photos = FakePhotos(PhotoRef('trap-1.jpg', copy.path))..pending = Completer<PhotoRef?>();
    final history = MemoryHistory();
    await tester.pumpWidget(RicePestApp(services: services(history: history, photos: photos)));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Take a photo of the trap'));
    await tester.pump();
    await tester.pumpWidget(const SizedBox());
    photos.pending!.complete(photos.next);
    await tester.pumpAndSettle();
    expect(tester.takeException(), isNull);
    expect(history.entries, isEmpty);
    expect(copy.existsSync(), isFalse);
  });

  testWidgets('Settings cannot be opened while a count is running', (tester) async {
    final detector = GateDetector();
    await tester.pumpWidget(RicePestApp(services: services(detector: detector)));
    await tester.pumpAndSettle();
    expect(tester.widget<IconButton>(settingsButton).onPressed, isNotNull);
    await tester.tap(find.text('Take a photo of the trap'));
    await tester.pump();
    expect(find.text('Counting insects…'), findsOneWidget);
    expect(tester.widget<IconButton>(settingsButton).onPressed, isNull);
    detector.gate.complete();
    await tester.pumpAndSettle();
    await tester.pageBack();
    await tester.pumpAndSettle();
    expect(tester.widget<IconButton>(settingsButton).onPressed, isNotNull);
  });
}
