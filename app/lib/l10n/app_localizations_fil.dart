// ignore: unused_import
import 'package:intl/intl.dart' as intl;

import 'app_localizations.dart';

// ignore_for_file: type=lint

/// The translations for Filipino Pilipino (`fil`).
class AppLocalizationsFil extends AppLocalizations {
  AppLocalizationsFil([String locale = 'fil']) : super(locale);

  @override
  String get appTitle => 'Pambilang ng Peste sa Bitag';

  @override
  String get modelNotice =>
      'Eksperimental na modelo. Tantiya lamang ang bilang at hindi ito para sa pagpapasya tungkol sa pagkontrol ng peste.';

  @override
  String get demoNotice =>
      'Demo: tunay na model weights, na may threshold na pinili gamit ang mga validation photo. Hindi pa napapatunayan sa bukid ang mga bilang.';

  @override
  String get noModelNotice =>
      'Wala pang naka-install na modelo, kaya hindi pa makabibilang ng insekto ang app. Mabubuksan pa rin ang mga dating bilang.';

  @override
  String get takePhoto => 'Kunan ng litrato ang bitag';

  @override
  String get choosePhoto => 'Pumili ng litrato';

  @override
  String get history => 'Mga nakaraang bilang';

  @override
  String get noHistory => 'Wala pang bilang.';

  @override
  String get analysing => 'Binibilang ang mga insekto…';

  @override
  String get resultTitle => 'Bilang';

  @override
  String get speciesRBB => 'Atangya (rice black bug)';

  @override
  String get speciesWSB => 'Puting aksip (white stemborer)';

  @override
  String get needsReview => 'Pakisuri ang bilang na ito sa litrato';

  @override
  String get reviewLowConfidence => 'May mga insektong mahirap makilala.';

  @override
  String get reviewCrowded =>
      'Maraming insekto sa litrato: maaaring mali ang bilang.';

  @override
  String get shareCounts => 'Ibahagi ang mga bilang';

  @override
  String shareSummary(
    String date,
    int rbb,
    int wsb,
    String model,
    String threshold,
  ) {
    return 'Litrato ng bitag $date: atangya $rbb, puting aksip $wsb. Modelo $model, threshold $threshold. Tantiya lamang ang bilang; pakisuri.';
  }

  @override
  String modelInfo(String model, String threshold) {
    return 'Modelo $model · threshold $threshold';
  }

  @override
  String get deleteEntry => 'Burahin';

  @override
  String get photoTooSmall =>
      'Masyadong maliit ang litrato. Kunan nang mas malapit ang bitag.';

  @override
  String get photoTooLarge =>
      'Masyadong malaki ang litrato para bilangin. Pumili ng litratong 50 megapixel o mas maliit.';

  @override
  String get photoUnreadable => 'Hindi mabuksan ang file bilang litrato.';

  @override
  String get about => 'Tungkol sa app';

  @override
  String get intendedUse =>
      'Isang demonstrasyon para sa pagtuturo kung paano pinapatakbo ang isang modelo ng pagbilang ng peste sa telepono. Dalawang peste ang binibilang nito sa mga litrato ng light trap: atangya at puting aksip. Hindi ito ginawa para gamitin sa sakahan, hindi pa napapatunayan sa bukid, at hindi ito opisyal na kasangkapan ng anumang organisasyon. Tantiya lamang ang mga bilang at hindi ito para sa pagpapasya tungkol sa pagkontrol ng peste.';

  @override
  String get privacyNotice =>
      'Nananatili sa teleponong ito ang mga litrato at bilang. Walang ipinapadala maliban kung piliin ninyong ibahagi.';

  @override
  String get openSourceLicences => 'Mga lisensiya ng open-source';

  @override
  String get licences =>
      'Data: Deleña et al., light-trap rice pest dataset, CC BY 4.0 (doi.org/10.5281/zenodo.20066074), muling hinati sa mga bagong split. Code ng app at modelo: Apache-2.0.';

  @override
  String downloadModel(int size) {
    return 'I-download ang modelo ($size MB)';
  }

  @override
  String get downloading => 'Dina-download ang modelo…';

  @override
  String get downloadFailed =>
      'Hindi natapos ang pag-download ng modelo. Suriin ang koneksyon at subukan muli.';

  @override
  String get settings => 'Mga setting';

  @override
  String get modelSection => 'Modelo';

  @override
  String get modelListHint =>
      'Ang r50-v5 ang default na modelo. Ang iba ay demo na modelo para sa paghahambing lamang.';

  @override
  String get notValidatedBanner =>
      'Demo na modelo, hindi pa napapatunayan. Gamitin lamang ang mga bilang nito para ihambing sa default na modelo.';

  @override
  String get defaultTag => 'Default';

  @override
  String get activeTag => 'Ginagamit';

  @override
  String get notValidatedTag => 'Hindi pa napapatunayan';

  @override
  String modelDetails(
    String architecture,
    int size,
    String threshold,
    String accuracy,
    String baseline,
  ) {
    return '$architecture · $size px · threshold $threshold · katumpakan ng bilang $accuracy (kung walang gagawin: $baseline)';
  }

  @override
  String get noModelsInstalled => 'Walang naka-install na modelo.';

  @override
  String switchedModel(String label) {
    return 'Ginagamit na ang $label.';
  }

  @override
  String get switchFailed =>
      'Hindi ma-load ang modelong iyon. Ang dating modelo pa rin ang ginagamit.';

  @override
  String get importModel => 'Mag-import ng modelo mula sa file';

  @override
  String get importPickManifest =>
      'Piliin ang manifest file ng modelo (.json).';

  @override
  String get importPickModel => 'Ngayon, piliin ang file ng modelo (.onnx).';

  @override
  String get importChecking => 'Sinusuri ang modelo…';

  @override
  String importDone(String label) {
    return 'Na-import ang $label. I-tap ito para gamitin.';
  }

  @override
  String get importErrorManifest =>
      'Hindi wasto ang manifest file. Walang na-import.';

  @override
  String get importErrorSize =>
      'Hindi tugma ang laki ng file ng modelo sa nakasaad sa manifest. Walang na-import.';

  @override
  String get importErrorChecksum =>
      'Hindi tugma ang file ng modelo sa checksum ng manifest. Walang na-import.';

  @override
  String get importErrorShape =>
      'Hindi akma sa app na ito ang input o output ng modelo. Walang na-import.';

  @override
  String get importErrorSelfTest =>
      'Hindi pumasa ang modelo sa sarili nitong pagsusuri. Walang na-import.';

  @override
  String get importErrorExists =>
      'May naka-install nang modelo na may ganitong id. Walang na-import.';

  @override
  String get importErrorFile => 'Hindi mabasa ang mga file. Walang na-import.';

  @override
  String get deleteModel => 'Burahin ang modelo';

  @override
  String deleteModelConfirm(String label) {
    return 'Burahin ang $label sa teleponong ito?';
  }

  @override
  String get cancel => 'Kanselahin';

  @override
  String get compareModels => 'Paghambingin ang mga modelo sa isang litrato';

  @override
  String get compareTitle => 'Paghahambing ng mga modelo';

  @override
  String get compareNotice =>
      'Paghahambing ng mga demo na modelo: wala pang napapatunayan sa mga ito. Nananatili sa teleponong ito ang litrato at resulta, at hindi ito isinasama sa mga nakaraang bilang.';

  @override
  String compareProgress(int current, int total, String label) {
    return 'Pinapatakbo ang modelo $current sa $total: $label';
  }

  @override
  String compareTime(String seconds) {
    return '$seconds s';
  }

  @override
  String get compareNoFlags => 'Walang babala sa pagsusuri';

  @override
  String get compareFailed => 'Hindi nabilang ng modelong ito ang litrato.';

  @override
  String get downloadSection => 'Mag-download ng modelo';

  @override
  String get downloadHint =>
      'Mga nailathalang modelo. Kumokonekta lang ang app sa internet kapag pinindot mo ang I-download, at sinusuri nito ang bawat modelo bago ito magamit.';

  @override
  String get download => 'I-download';

  @override
  String get installedTag => 'Naka-install';

  @override
  String publishedDetails(
    String architecture,
    int size,
    String threshold,
    String accuracy,
    String baseline,
    int megabytes,
  ) {
    return '$architecture · $size px · threshold $threshold · katumpakan ng bilang $accuracy (kung walang gagawin: $baseline) · $megabytes MB';
  }

  @override
  String downloadProgress(String received, String total) {
    return 'Na-download ang $received sa $total MB';
  }

  @override
  String downloadProgressUnknown(String received) {
    return 'Na-download ang $received MB';
  }

  @override
  String get cancelDownload => 'Kanselahin ang pag-download';

  @override
  String get downloadCancelled =>
      'Kinansela ang pag-download. Walang na-install.';

  @override
  String downloadDone(String label) {
    return 'Na-download ang $label. I-tap ito para gamitin.';
  }

  @override
  String get downloadErrorNetwork =>
      'Hindi natapos ang pag-download. Suriin ang koneksyon at subukan muli. Walang na-install.';

  @override
  String get downloadErrorSize =>
      'Hindi tugma ang laki ng na-download na file sa inaasahan. Walang na-install.';

  @override
  String get downloadErrorChecksum =>
      'Hindi tugma ang na-download na file sa checksum nito. Walang na-install.';

  @override
  String get downloadErrorCheck =>
      'Hindi pumasa ang na-download na modelo sa pagsusuri. Walang na-install.';

  @override
  String errorWithDetail(String message, String detail) {
    return '$message\nDetalye: $detail';
  }
}
