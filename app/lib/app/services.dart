// Everything the screens need from the outside world, so tests can swap in fakes.
import 'dart:io';

import '../counting/counting.dart';
import '../inference/contract.dart';
import '../inference/detector.dart';
import '../model/model_registry.dart';
import '../model/model_store.dart';
import '../model/published_models.dart';
import '../storage/history.dart';

abstract class PhotoSource {
  Future<PhotoRef?> camera();
  Future<PhotoRef?> gallery();
}

abstract class Sharer {
  Future<void> share(String text, {String? photoPath});
}

/// Which model is running, which decides the notice shown to the user.
enum ModelMode {
  /// No model installed: the app cannot count, and says so. Past counts can still be opened.
  none,

  /// Real trained weights with a demo threshold chosen on validation data; not release-gated.
  demo,

  /// A pinned, published model that passed the release gates.
  published,
}

/// A pinned model the home screen can download (size and SHA-256 are verified by ModelStore).
class ModelDownload {
  const ModelDownload({required this.bytes, required this.label, required this.run});
  final int bytes;
  final String label;

  /// Downloads and verifies the file; throws ModelDownloadFailed or ModelVerificationFailed.
  final Future<void> Function() run;
}

/// The installed models, for Settings (switch, import, delete) and the compare screen.
abstract class ModelCatalog {
  Future<List<InstalledModel>> list();

  /// Makes [id] the model used from the next start-up choice; null falls back to the default.
  Future<void> activate(String? id);

  /// Removes an imported model; the default model cannot be removed.
  Future<void> delete(String id);

  /// Copies and verifies a model and its manifest; throws ModelImportFailed. Does not activate it.
  Future<InstalledModel> importFrom({required File model, required File manifest});

  /// The published models from the bundled catalogue, offered for download in Settings.
  List<PublishedModel> get published;

  /// Downloads [model] from its catalogue URL and installs it with the same checks as [importFrom]. Throws
  /// ModelDownloadFailed (network), ModelImportFailed (size, checksum or session check) or
  /// DownloadCancelled; any failure leaves no files. Does not activate it.
  Future<InstalledModel> download(PublishedModel model,
      {void Function(int received, int? total)? onProgress, DownloadCancel? cancel});

  /// Loads one model's detector; release it with [close] before loading the next.
  Future<Detector> open(InstalledModel model);
  Future<void> close(Detector detector);
}

/// Lets the person using the app (or a tester) pick a model file and its manifest on the phone. Never a
/// URL: downloads come only from the bundled catalogue.
abstract class ModelFilePicker {
  Future<File?> pickManifest();
  Future<File?> pickModel();
}

class AppServices {
  AppServices({this.detector, required this.history, required this.photos, required this.sharer,
      required this.mode, this.threshold = defaultThreshold, this.reviewBelow = defaultReviewBelow,
      this.download, this.activeModel, this.models, this.modelFiles, this.release, DateTime Function()? now,
      String Function()? newId})
      : assert((detector == null) == (mode == ModelMode.none), 'a detector exactly when a model is installed'),
        now = now ?? DateTime.now,
        newId = newId ?? (() => DateTime.now().microsecondsSinceEpoch.toString());

  /// Null only in [ModelMode.none].
  final Detector? detector;
  final History history;
  final PhotoSource photos;
  final Sharer sharer;
  final ModelMode mode;

  /// Counting threshold; recorded with every count.
  final double threshold;

  /// The active model's low-confidence review flag.
  final double reviewBelow;

  /// The model behind [detector]; null when none is installed (and in older tests).
  final InstalledModel? activeModel;

  /// Null only in tests that do not exercise Settings.
  final ModelCatalog? models;
  final ModelFilePicker? modelFiles;

  /// Frees the detector's native session once these services are replaced.
  final Future<void> Function()? release;

  /// Every model other than the default shows the "Demo model, not validated" banner.
  bool get notValidated => activeModel != null && !activeModel!.isDefault;

  /// Offered on the home screen when no model is installed but one is pinned.
  final ModelDownload? download;
  final DateTime Function() now;
  final String Function() newId;
}

/// Shown on screens and in shared summaries; local time, locale-independent.
String formatTakenAt(DateTime t) {
  final l = t.toLocal();
  String two(int v) => v.toString().padLeft(2, '0');
  return '${l.year}-${two(l.month)}-${two(l.day)} ${two(l.hour)}:${two(l.minute)}';
}
