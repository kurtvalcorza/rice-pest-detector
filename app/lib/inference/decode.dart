// Decode a photo file into upright RGB pixels, so the contract then runs with orientation 1.
//
// The image package's JPEG decoder applies the EXIF orientation itself and clears the tag;
// other formats keep the tag and are rotated here with applyExifOrientation, which is validated
// against Pillow's exif_transpose. decode_test checks the JPEG path matches Pillow for tags 1-8.
//
// JPEG decoders differ by a level or two per pixel (IDCT and colour conversion), so real-photo
// parity with Python is detection-level (the export parity tolerance), not byte-level.
import 'dart:typed_data';

import 'package:image/image.dart' as img;

import 'preprocess.dart';

class PhotoUnreadable implements Exception {
  @override
  String toString() => 'This file is not a readable photo';
}

/// Photos with more pixels than this are refused before they are decoded: a small file can declare huge
/// dimensions (a 435 KB PNG of 12000 x 12000 needs about 900 MB to decode). 50 MP still covers the
/// high-resolution modes of phone cameras.
const int maxPhotoPixels = 50 * 1000 * 1000;

class PhotoTooLarge implements Exception {
  PhotoTooLarge(this.width, this.height);
  final int width;
  final int height;
  @override
  String toString() => 'Photo is ${width}x$height, more than $maxPhotoPixels pixels';
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
  final info = img.findDecoderForData(data)?.startDecode(data);
  // A header with no size (an ICO wrapper reports 0x0) cannot be checked against the limit.
  if (info == null || info.width <= 0 || info.height <= 0) throw PhotoUnreadable();
  if (info.width * info.height > maxPhotoPixels) throw PhotoTooLarge(info.width, info.height);
  final decoded = img.decodeImage(data, frame: 0); // only the first frame: the limit is per frame
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
