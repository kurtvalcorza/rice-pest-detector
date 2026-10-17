// Decode a photo file into upright RGB pixels, so the contract then runs with orientation 1.
//
// The image package's JPEG decoder applies the EXIF orientation itself and clears the tag;
// other formats keep the tag and are rotated here with applyExifOrientation, which is validated
// against Pillow's exif_transpose. decode_test checks the JPEG path matches Pillow for tags 1-8.
//
// JPEG decoders differ by a level or two per pixel (IDCT and colour conversion), so real-photo
// parity with Python is detection-level (spec §4.5 tolerance), not byte-level.
import 'dart:typed_data';

import 'package:image/image.dart' as img;

import 'preprocess.dart';

class PhotoUnreadable implements Exception {
  @override
  String toString() => 'This file is not a readable photo';
}

class DecodedPhoto {
  DecodedPhoto(this.image, this.orientationTag);

  /// Upright pixels: the EXIF orientation has already been applied.
  final RgbImage image;

  /// The EXIF orientation tag the file carried (1 when absent), kept for the record.
  final int orientationTag;
}

DecodedPhoto decodePhoto(List<int> bytes) {
  final data = bytes is Uint8List ? bytes : Uint8List.fromList(bytes);
  final decoded = img.decodeImage(data);
  if (decoded == null) throw PhotoUnreadable();
  final rgb = decoded.numChannels == 3 && decoded.format == img.Format.uint8 && !decoded.hasPalette
      ? decoded
      : decoded.convert(numChannels: 3, format: img.Format.uint8);
  var upright = RgbImage(rgb.width, rgb.height,
      Uint8List.fromList(rgb.getBytes(order: img.ChannelOrder.rgb)));
  final residual = decoded.exif.imageIfd.orientation; // still present => the decoder left it
  if (residual != null && residual >= 2 && residual <= 8) {
    upright = applyExifOrientation(upright, residual);
    return DecodedPhoto(upright, residual);
  }
  final tag = residual ?? img.decodeJpgExif(data)?.imageIfd.orientation ?? 1;
  return DecodedPhoto(upright, tag >= 1 && tag <= 8 ? tag : 1);
}
