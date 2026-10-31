// ignore: unused_import
import 'package:intl/intl.dart' as intl;

import 'app_localizations.dart';

// ignore_for_file: type=lint

/// The translations for English (`en`).
class AppLocalizationsEn extends AppLocalizations {
  AppLocalizationsEn([String locale = 'en']) : super(locale);

  @override
  String get appTitle => 'Trap Pest Counter';

  @override
  String get modelNotice =>
      'Experimental model. Counts are estimates and are not for pest-management decisions.';

  @override
  String get demoNotice =>
      'Demo: real model weights, with a counting threshold chosen on validation photos. The counts have not been validated in the field.';

  @override
  String get noModelNotice =>
      'No model is installed yet, so the app cannot count insects. Past counts can still be opened.';

  @override
  String get takePhoto => 'Take a photo of the trap';

  @override
  String get choosePhoto => 'Choose a photo';

  @override
  String get history => 'Past counts';

  @override
  String get noHistory => 'No counts yet.';

  @override
  String get analysing => 'Counting insects…';

  @override
  String get resultTitle => 'Count';

  @override
  String get speciesRBB => 'Rice black bug (atangya)';

  @override
  String get speciesWSB => 'White stemborer (puting aksip)';

  @override
  String get needsReview => 'Please check this count against the photo';

  @override
  String get reviewLowConfidence => 'Some insects were hard to recognise.';

  @override
  String get reviewCrowded =>
      'Many insects in the photo: the count may be off.';

  @override
  String get shareCounts => 'Share the counts';

  @override
  String shareSummary(
    String date,
    int rbb,
    int wsb,
    String model,
    String threshold,
  ) {
    return 'Trap photo $date: rice black bug $rbb, white stemborer $wsb. Model $model, threshold $threshold. Counts are estimates; please review.';
  }

  @override
  String modelInfo(String model, String threshold) {
    return 'Model $model · threshold $threshold';
  }

  @override
  String get deleteEntry => 'Delete';

  @override
  String get photoTooSmall =>
      'This photo is too small. Take a closer photo of the trap.';

  @override
  String get photoTooLarge =>
      'This photo is too large to count. Choose a photo of 50 megapixels or less.';

  @override
  String get photoUnreadable => 'This file could not be opened as a photo.';

  @override
  String get analysisFailed =>
      'This photo could not be counted, and nothing was saved. Try again.';

  @override
  String get about => 'About';

  @override
  String get intendedUse =>
      'A teaching demonstration of running a pest-counting model on a phone. It counts two pests in light-trap photos: rice black bug and white stemborer. It is not made for farm use, has not been validated in the field, and is not an official tool of any organisation. The counts are estimates and are not for pest-management decisions.';

  @override
  String get privacyNotice =>
      'Photos and counts stay on this phone. Nothing is sent unless you choose to share it.';

  @override
  String get openSourceLicences => 'Open-source licences';

  @override
  String get licences =>
      'Data: Deleña et al., light-trap rice pest dataset, CC BY 4.0 (doi.org/10.5281/zenodo.20066074), regrouped into new splits. App and model code: Apache-2.0.';

  @override
  String downloadModel(int size) {
    return 'Download the model ($size MB)';
  }

  @override
  String get downloading => 'Downloading the model…';

  @override
  String get downloadFailed =>
      'The model download failed. Check the connection and try again.';

  @override
  String get settings => 'Settings';

  @override
  String get modelSection => 'Model';

  @override
  String get modelListHint =>
      'r50-v5 is the default model. The others are demo models for comparison only.';

  @override
  String get notValidatedBanner =>
      'Demo model, not validated. Use its counts only for comparison with the default model.';

  @override
  String get defaultTag => 'Default';

  @override
  String get activeTag => 'In use';

  @override
  String get notValidatedTag => 'Not validated';

  @override
  String modelDetails(
    String architecture,
    int size,
    String threshold,
    String accuracy,
    String baseline,
  ) {
    return '$architecture · $size px · threshold $threshold · count accuracy $accuracy (doing nothing: $baseline)';
  }

  @override
  String get noModelsInstalled => 'No models are installed.';

  @override
  String switchedModel(String label) {
    return 'Now using $label.';
  }

  @override
  String get switchFailed =>
      'That model could not be loaded. The previous model is still in use.';

  @override
  String get importModel => 'Import a model from a file';

  @override
  String get importPickManifest => 'Choose the model\'s manifest file (.json).';

  @override
  String get importPickModel => 'Now choose the model file (.onnx).';

  @override
  String get importChecking => 'Checking the model…';

  @override
  String importDone(String label) {
    return 'Imported $label. Tap it to use it.';
  }

  @override
  String get importErrorManifest =>
      'The manifest file is not valid. Nothing was imported.';

  @override
  String get importErrorSize =>
      'The model file is not the size its manifest gives. Nothing was imported.';

  @override
  String get importErrorChecksum =>
      'The model file does not match its manifest checksum. Nothing was imported.';

  @override
  String get importErrorShape =>
      'The model\'s inputs or outputs do not fit this app. Nothing was imported.';

  @override
  String get importErrorSelfTest =>
      'The model failed its self-test. Nothing was imported.';

  @override
  String get importErrorExists =>
      'A model with this id is already installed. Nothing was imported.';

  @override
  String get importErrorFile =>
      'The files could not be read. Nothing was imported.';

  @override
  String get deleteModel => 'Delete model';

  @override
  String deleteModelConfirm(String label) {
    return 'Delete $label from this phone?';
  }

  @override
  String get cancel => 'Cancel';

  @override
  String get compareModels => 'Compare models on one photo';

  @override
  String get compareTitle => 'Model comparison';

  @override
  String get compareNotice =>
      'Comparison of demo models: none of them is validated. The photo and results stay on this phone and are not saved to past counts.';

  @override
  String compareProgress(int current, int total, String label) {
    return 'Running model $current of $total: $label';
  }

  @override
  String compareTime(String seconds) {
    return '$seconds s';
  }

  @override
  String get compareNoFlags => 'No review flags';

  @override
  String get compareFailed => 'This model could not count this photo.';

  @override
  String get downloadSection => 'Download a model';

  @override
  String get downloadHint =>
      'Published models. The app connects to the internet only when you tap Download, and checks each model before it can be used.';

  @override
  String get download => 'Download';

  @override
  String get installedTag => 'Installed';

  @override
  String publishedDetails(
    String architecture,
    int size,
    String threshold,
    String accuracy,
    String baseline,
    int megabytes,
  ) {
    return '$architecture · $size px · threshold $threshold · count accuracy $accuracy (doing nothing: $baseline) · $megabytes MB';
  }

  @override
  String downloadProgress(String received, String total) {
    return 'Downloaded $received of $total MB';
  }

  @override
  String downloadProgressUnknown(String received) {
    return 'Downloaded $received MB';
  }

  @override
  String get cancelDownload => 'Cancel download';

  @override
  String get downloadCancelled => 'Download cancelled. Nothing was installed.';

  @override
  String downloadDone(String label) {
    return 'Downloaded $label. Tap it to use it.';
  }

  @override
  String get downloadErrorNetwork =>
      'The download failed. Check the connection and try again. Nothing was installed.';

  @override
  String get downloadErrorSize =>
      'The downloaded file is not the expected size. Nothing was installed.';

  @override
  String get downloadErrorChecksum =>
      'The downloaded file does not match its checksum. Nothing was installed.';

  @override
  String get downloadErrorCheck =>
      'The downloaded model failed its checks. Nothing was installed.';

  @override
  String errorWithDetail(String message, String detail) {
    return '$message\nDetails: $detail';
  }
}
