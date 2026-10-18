import 'dart:async';

import 'package:flutter/foundation.dart';
import 'package:flutter/widgets.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:intl/intl.dart' as intl;

import 'app_localizations_en.dart';
import 'app_localizations_fil.dart';

// ignore_for_file: type=lint

/// Callers can lookup localized strings with an instance of AppLocalizations
/// returned by `AppLocalizations.of(context)`.
///
/// Applications need to include `AppLocalizations.delegate()` in their app's
/// `localizationDelegates` list, and the locales they support in the app's
/// `supportedLocales` list. For example:
///
/// ```dart
/// import 'l10n/app_localizations.dart';
///
/// return MaterialApp(
///   localizationsDelegates: AppLocalizations.localizationsDelegates,
///   supportedLocales: AppLocalizations.supportedLocales,
///   home: MyApplicationHome(),
/// );
/// ```
///
/// ## Update pubspec.yaml
///
/// Please make sure to update your pubspec.yaml to include the following
/// packages:
///
/// ```yaml
/// dependencies:
///   # Internationalization support.
///   flutter_localizations:
///     sdk: flutter
///   intl: any # Use the pinned version from flutter_localizations
///
///   # Rest of dependencies
/// ```
///
/// ## iOS Applications
///
/// iOS applications define key application metadata, including supported
/// locales, in an Info.plist file that is built into the application bundle.
/// To configure the locales supported by your app, you’ll need to edit this
/// file.
///
/// First, open your project’s ios/Runner.xcworkspace Xcode workspace file.
/// Then, in the Project Navigator, open the Info.plist file under the Runner
/// project’s Runner folder.
///
/// Next, select the Information Property List item, select Add Item from the
/// Editor menu, then select Localizations from the pop-up menu.
///
/// Select and expand the newly-created Localizations item then, for each
/// locale your application supports, add a new item and select the locale
/// you wish to add from the pop-up menu in the Value field. This list should
/// be consistent with the languages listed in the AppLocalizations.supportedLocales
/// property.
abstract class AppLocalizations {
  AppLocalizations(String locale)
    : localeName = intl.Intl.canonicalizedLocale(locale.toString());

  final String localeName;

  static AppLocalizations of(BuildContext context) {
    return Localizations.of<AppLocalizations>(context, AppLocalizations)!;
  }

  static const LocalizationsDelegate<AppLocalizations> delegate =
      _AppLocalizationsDelegate();

  /// A list of this localizations delegate along with the default localizations
  /// delegates.
  ///
  /// Returns a list of localizations delegates containing this delegate along with
  /// GlobalMaterialLocalizations.delegate, GlobalCupertinoLocalizations.delegate,
  /// and GlobalWidgetsLocalizations.delegate.
  ///
  /// Additional delegates can be added by appending to this list in
  /// MaterialApp. This list does not have to be used at all if a custom list
  /// of delegates is preferred or required.
  static const List<LocalizationsDelegate<dynamic>> localizationsDelegates =
      <LocalizationsDelegate<dynamic>>[
        delegate,
        GlobalMaterialLocalizations.delegate,
        GlobalCupertinoLocalizations.delegate,
        GlobalWidgetsLocalizations.delegate,
      ];

  /// A list of this localizations delegate's supported locales.
  static const List<Locale> supportedLocales = <Locale>[
    Locale('en'),
    Locale('fil'),
  ];

  /// No description provided for @appTitle.
  ///
  /// In en, this message translates to:
  /// **'Trap Pest Counter'**
  String get appTitle;

  /// No description provided for @modelNotice.
  ///
  /// In en, this message translates to:
  /// **'Experimental model. Counts are estimates and are not for pest-management decisions.'**
  String get modelNotice;

  /// No description provided for @demoNotice.
  ///
  /// In en, this message translates to:
  /// **'Demo: real model weights, with a counting threshold chosen on validation photos. The counts have not been validated in the field.'**
  String get demoNotice;

  /// No description provided for @noModelNotice.
  ///
  /// In en, this message translates to:
  /// **'No model is installed yet, so the app cannot count insects. Past counts can still be opened.'**
  String get noModelNotice;

  /// No description provided for @takePhoto.
  ///
  /// In en, this message translates to:
  /// **'Take a photo of the trap'**
  String get takePhoto;

  /// No description provided for @choosePhoto.
  ///
  /// In en, this message translates to:
  /// **'Choose a photo'**
  String get choosePhoto;

  /// No description provided for @history.
  ///
  /// In en, this message translates to:
  /// **'Past counts'**
  String get history;

  /// No description provided for @noHistory.
  ///
  /// In en, this message translates to:
  /// **'No counts yet.'**
  String get noHistory;

  /// No description provided for @analysing.
  ///
  /// In en, this message translates to:
  /// **'Counting insects…'**
  String get analysing;

  /// No description provided for @resultTitle.
  ///
  /// In en, this message translates to:
  /// **'Count'**
  String get resultTitle;

  /// No description provided for @speciesRBB.
  ///
  /// In en, this message translates to:
  /// **'Rice black bug (atangya)'**
  String get speciesRBB;

  /// No description provided for @speciesWSB.
  ///
  /// In en, this message translates to:
  /// **'White stemborer (puting aksip)'**
  String get speciesWSB;

  /// No description provided for @needsReview.
  ///
  /// In en, this message translates to:
  /// **'Please check this count against the photo'**
  String get needsReview;

  /// No description provided for @reviewLowConfidence.
  ///
  /// In en, this message translates to:
  /// **'Some insects were hard to recognise.'**
  String get reviewLowConfidence;

  /// No description provided for @reviewCrowded.
  ///
  /// In en, this message translates to:
  /// **'Many insects in the photo: the count may be off.'**
  String get reviewCrowded;

  /// No description provided for @shareCounts.
  ///
  /// In en, this message translates to:
  /// **'Share the counts'**
  String get shareCounts;

  /// No description provided for @shareSummary.
  ///
  /// In en, this message translates to:
  /// **'Trap photo {date}: rice black bug {rbb}, white stemborer {wsb}. Model {model}, threshold {threshold}. Counts are estimates; please review.'**
  String shareSummary(
    String date,
    int rbb,
    int wsb,
    String model,
    String threshold,
  );

  /// No description provided for @modelInfo.
  ///
  /// In en, this message translates to:
  /// **'Model {model} · threshold {threshold}'**
  String modelInfo(String model, String threshold);

  /// No description provided for @deleteEntry.
  ///
  /// In en, this message translates to:
  /// **'Delete'**
  String get deleteEntry;

  /// No description provided for @photoTooSmall.
  ///
  /// In en, this message translates to:
  /// **'This photo is too small. Take a closer photo of the trap.'**
  String get photoTooSmall;

  /// No description provided for @photoUnreadable.
  ///
  /// In en, this message translates to:
  /// **'This file could not be opened as a photo.'**
  String get photoUnreadable;

  /// No description provided for @about.
  ///
  /// In en, this message translates to:
  /// **'About'**
  String get about;

  /// No description provided for @intendedUse.
  ///
  /// In en, this message translates to:
  /// **'A teaching demonstration of running a pest-counting model on a phone. It counts two pests in light-trap photos: rice black bug and white stemborer. It is not made for farm use, has not been validated in the field, and is not an official tool of any organisation. The counts are estimates and are not for pest-management decisions.'**
  String get intendedUse;

  /// No description provided for @privacyNotice.
  ///
  /// In en, this message translates to:
  /// **'Photos and counts stay on this phone. Nothing is sent unless you choose to share it.'**
  String get privacyNotice;

  /// No description provided for @openSourceLicences.
  ///
  /// In en, this message translates to:
  /// **'Open-source licences'**
  String get openSourceLicences;

  /// No description provided for @licences.
  ///
  /// In en, this message translates to:
  /// **'Data: Deleña et al., light-trap rice pest dataset, CC BY 4.0 (doi.org/10.5281/zenodo.20066074), regrouped into new splits. App and model code: Apache-2.0.'**
  String get licences;

  /// No description provided for @downloadModel.
  ///
  /// In en, this message translates to:
  /// **'Download the model ({size} MB)'**
  String downloadModel(int size);

  /// No description provided for @downloading.
  ///
  /// In en, this message translates to:
  /// **'Downloading the model…'**
  String get downloading;

  /// No description provided for @downloadFailed.
  ///
  /// In en, this message translates to:
  /// **'The model download failed. Check the connection and try again.'**
  String get downloadFailed;

  /// No description provided for @settings.
  ///
  /// In en, this message translates to:
  /// **'Settings'**
  String get settings;

  /// No description provided for @modelSection.
  ///
  /// In en, this message translates to:
  /// **'Model'**
  String get modelSection;

  /// No description provided for @modelListHint.
  ///
  /// In en, this message translates to:
  /// **'r50-v5 is the default model. The others are demo models for comparison only.'**
  String get modelListHint;

  /// No description provided for @notValidatedBanner.
  ///
  /// In en, this message translates to:
  /// **'Demo model, not validated. Use its counts only for comparison with the default model.'**
  String get notValidatedBanner;

  /// No description provided for @defaultTag.
  ///
  /// In en, this message translates to:
  /// **'Default'**
  String get defaultTag;

  /// No description provided for @activeTag.
  ///
  /// In en, this message translates to:
  /// **'In use'**
  String get activeTag;

  /// No description provided for @notValidatedTag.
  ///
  /// In en, this message translates to:
  /// **'Not validated'**
  String get notValidatedTag;

  /// No description provided for @modelDetails.
  ///
  /// In en, this message translates to:
  /// **'{architecture} · {size} px · threshold {threshold} · count accuracy {accuracy} (doing nothing: {baseline})'**
  String modelDetails(
    String architecture,
    int size,
    String threshold,
    String accuracy,
    String baseline,
  );

  /// No description provided for @noModelsInstalled.
  ///
  /// In en, this message translates to:
  /// **'No models are installed.'**
  String get noModelsInstalled;

  /// No description provided for @switchedModel.
  ///
  /// In en, this message translates to:
  /// **'Now using {label}.'**
  String switchedModel(String label);

  /// No description provided for @switchFailed.
  ///
  /// In en, this message translates to:
  /// **'That model could not be loaded. The previous model is still in use.'**
  String get switchFailed;

  /// No description provided for @importModel.
  ///
  /// In en, this message translates to:
  /// **'Import a model from a file'**
  String get importModel;

  /// No description provided for @importPickManifest.
  ///
  /// In en, this message translates to:
  /// **'Choose the model\'s manifest file (.json).'**
  String get importPickManifest;

  /// No description provided for @importPickModel.
  ///
  /// In en, this message translates to:
  /// **'Now choose the model file (.onnx).'**
  String get importPickModel;

  /// No description provided for @importChecking.
  ///
  /// In en, this message translates to:
  /// **'Checking the model…'**
  String get importChecking;

  /// No description provided for @importDone.
  ///
  /// In en, this message translates to:
  /// **'Imported {label}. Tap it to use it.'**
  String importDone(String label);

  /// No description provided for @importErrorManifest.
  ///
  /// In en, this message translates to:
  /// **'The manifest file is not valid. Nothing was imported.'**
  String get importErrorManifest;

  /// No description provided for @importErrorSize.
  ///
  /// In en, this message translates to:
  /// **'The model file is not the size its manifest gives. Nothing was imported.'**
  String get importErrorSize;

  /// No description provided for @importErrorChecksum.
  ///
  /// In en, this message translates to:
  /// **'The model file does not match its manifest checksum. Nothing was imported.'**
  String get importErrorChecksum;

  /// No description provided for @importErrorShape.
  ///
  /// In en, this message translates to:
  /// **'The model\'s inputs or outputs do not fit this app. Nothing was imported.'**
  String get importErrorShape;

  /// No description provided for @importErrorSelfTest.
  ///
  /// In en, this message translates to:
  /// **'The model failed its self-test. Nothing was imported.'**
  String get importErrorSelfTest;

  /// No description provided for @importErrorExists.
  ///
  /// In en, this message translates to:
  /// **'A model with this id is already installed. Nothing was imported.'**
  String get importErrorExists;

  /// No description provided for @importErrorFile.
  ///
  /// In en, this message translates to:
  /// **'The files could not be read. Nothing was imported.'**
  String get importErrorFile;

  /// No description provided for @deleteModel.
  ///
  /// In en, this message translates to:
  /// **'Delete model'**
  String get deleteModel;

  /// No description provided for @deleteModelConfirm.
  ///
  /// In en, this message translates to:
  /// **'Delete {label} from this phone?'**
  String deleteModelConfirm(String label);

  /// No description provided for @cancel.
  ///
  /// In en, this message translates to:
  /// **'Cancel'**
  String get cancel;

  /// No description provided for @compareModels.
  ///
  /// In en, this message translates to:
  /// **'Compare models on one photo'**
  String get compareModels;

  /// No description provided for @compareTitle.
  ///
  /// In en, this message translates to:
  /// **'Model comparison'**
  String get compareTitle;

  /// No description provided for @compareNotice.
  ///
  /// In en, this message translates to:
  /// **'Comparison of demo models: none of them is validated. The photo and results stay on this phone and are not saved to past counts.'**
  String get compareNotice;

  /// No description provided for @compareProgress.
  ///
  /// In en, this message translates to:
  /// **'Running model {current} of {total}: {label}'**
  String compareProgress(int current, int total, String label);

  /// No description provided for @compareTime.
  ///
  /// In en, this message translates to:
  /// **'{seconds} s'**
  String compareTime(String seconds);

  /// No description provided for @compareNoFlags.
  ///
  /// In en, this message translates to:
  /// **'No review flags'**
  String get compareNoFlags;

  /// No description provided for @compareFailed.
  ///
  /// In en, this message translates to:
  /// **'This model could not count this photo.'**
  String get compareFailed;

  /// No description provided for @downloadSection.
  ///
  /// In en, this message translates to:
  /// **'Download a model'**
  String get downloadSection;

  /// No description provided for @downloadHint.
  ///
  /// In en, this message translates to:
  /// **'Published models. The app connects to the internet only when you tap Download, and checks each model before it can be used.'**
  String get downloadHint;

  /// No description provided for @download.
  ///
  /// In en, this message translates to:
  /// **'Download'**
  String get download;

  /// No description provided for @installedTag.
  ///
  /// In en, this message translates to:
  /// **'Installed'**
  String get installedTag;

  /// No description provided for @publishedDetails.
  ///
  /// In en, this message translates to:
  /// **'{architecture} · {size} px · threshold {threshold} · count accuracy {accuracy} (doing nothing: {baseline}) · {megabytes} MB'**
  String publishedDetails(
    String architecture,
    int size,
    String threshold,
    String accuracy,
    String baseline,
    int megabytes,
  );

  /// No description provided for @downloadProgress.
  ///
  /// In en, this message translates to:
  /// **'Downloaded {received} of {total} MB'**
  String downloadProgress(String received, String total);

  /// No description provided for @downloadProgressUnknown.
  ///
  /// In en, this message translates to:
  /// **'Downloaded {received} MB'**
  String downloadProgressUnknown(String received);

  /// No description provided for @cancelDownload.
  ///
  /// In en, this message translates to:
  /// **'Cancel download'**
  String get cancelDownload;

  /// No description provided for @downloadCancelled.
  ///
  /// In en, this message translates to:
  /// **'Download cancelled. Nothing was installed.'**
  String get downloadCancelled;

  /// No description provided for @downloadDone.
  ///
  /// In en, this message translates to:
  /// **'Downloaded {label}. Tap it to use it.'**
  String downloadDone(String label);

  /// No description provided for @downloadErrorNetwork.
  ///
  /// In en, this message translates to:
  /// **'The download failed. Check the connection and try again. Nothing was installed.'**
  String get downloadErrorNetwork;

  /// No description provided for @downloadErrorSize.
  ///
  /// In en, this message translates to:
  /// **'The downloaded file is not the expected size. Nothing was installed.'**
  String get downloadErrorSize;

  /// No description provided for @downloadErrorChecksum.
  ///
  /// In en, this message translates to:
  /// **'The downloaded file does not match its checksum. Nothing was installed.'**
  String get downloadErrorChecksum;

  /// No description provided for @downloadErrorCheck.
  ///
  /// In en, this message translates to:
  /// **'The downloaded model failed its checks. Nothing was installed.'**
  String get downloadErrorCheck;
}

class _AppLocalizationsDelegate
    extends LocalizationsDelegate<AppLocalizations> {
  const _AppLocalizationsDelegate();

  @override
  Future<AppLocalizations> load(Locale locale) {
    return SynchronousFuture<AppLocalizations>(lookupAppLocalizations(locale));
  }

  @override
  bool isSupported(Locale locale) =>
      <String>['en', 'fil'].contains(locale.languageCode);

  @override
  bool shouldReload(_AppLocalizationsDelegate old) => false;
}

AppLocalizations lookupAppLocalizations(Locale locale) {
  // Lookup logic when only language code is specified.
  switch (locale.languageCode) {
    case 'en':
      return AppLocalizationsEn();
    case 'fil':
      return AppLocalizationsFil();
  }

  throw FlutterError(
    'AppLocalizations.delegate failed to load unsupported locale "$locale". This is likely '
    'an issue with the localizations generation tool. Please file an issue '
    'on GitHub with a reproducible sample app and the gen-l10n configuration '
    'that was used.',
  );
}
