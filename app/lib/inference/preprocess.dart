// Pre-processing that reproduces rice_pest_detector.infer.preprocess exactly:
// EXIF orientation -> RGB -> Pillow BILINEAR resize to the model's square input size (640x640 by
// contract default, no letterbox) -> /255 -> NCHW float32.
import 'dart:math' as math;
import 'dart:typed_data';

import 'contract.dart';

/// Packed 8-bit RGB pixels, row-major.
class RgbImage {
  RgbImage(this.width, this.height, this.pixels)
      : assert(pixels.length == width * height * 3);
  final int width;
  final int height;
  final Uint8List pixels;
}

/// Pillow's ImageOps.exif_transpose for orientation tags 1-8 (1 = unchanged).
RgbImage applyExifOrientation(RgbImage img, int orientation) {
  final w = img.width, h = img.height, src = img.pixels;
  final swap = orientation >= 5 && orientation <= 8;
  final ow = swap ? h : w, oh = swap ? w : h;
  final out = Uint8List(ow * oh * 3);
  for (var y = 0; y < oh; y++) {
    for (var x = 0; x < ow; x++) {
      late int sx, sy;
      switch (orientation) {
        case 2: sx = w - 1 - x; sy = y; // FLIP_LEFT_RIGHT
        case 3: sx = w - 1 - x; sy = h - 1 - y; // ROTATE_180
        case 4: sx = x; sy = h - 1 - y; // FLIP_TOP_BOTTOM
        case 5: sx = y; sy = x; // TRANSPOSE
        case 6: sx = y; sy = h - 1 - x; // ROTATE_270
        case 7: sx = w - 1 - y; sy = h - 1 - x; // TRANSVERSE
        case 8: sx = w - 1 - y; sy = x; // ROTATE_90
        default: sx = x; sy = y;
      }
      final o = (y * ow + x) * 3, s = (sy * w + sx) * 3;
      out[o] = src[s];
      out[o + 1] = src[s + 1];
      out[o + 2] = src[s + 2];
    }
  }
  return RgbImage(ow, oh, out);
}

// Port of Pillow's libImaging/Resample.c (8-bit path): triangle filter widened when downscaling,
// coefficients normalised then fixed-point with PRECISION_BITS = 22, horizontal pass first.
const int _precisionBits = 32 - 8 - 2;

class _Coeffs {
  _Coeffs(this.ksize, this.bounds, this.kk);
  final int ksize;
  final Int32List bounds; // [xmin, count] per output pixel
  final Int32List kk; // fixed-point weights, ksize per output pixel
}

double _bilinear(double x) {
  x = x.abs();
  return x < 1.0 ? 1.0 - x : 0.0;
}

_Coeffs _precompute(int inSize, int outSize) {
  final scale = inSize / outSize;
  final filterscale = scale < 1.0 ? 1.0 : scale;
  final support = 1.0 * filterscale;
  final ksize = support.ceil() * 2 + 1;
  final bounds = Int32List(outSize * 2);
  final pre = Float64List(outSize * ksize);
  for (var xx = 0; xx < outSize; xx++) {
    final center = (xx + 0.5) * scale;
    final ss = 1.0 / filterscale;
    var xmin = (center - support + 0.5).toInt();
    if (xmin < 0) xmin = 0;
    var xmax = (center + support + 0.5).toInt();
    if (xmax > inSize) xmax = inSize;
    xmax -= xmin;
    var ww = 0.0;
    for (var x = 0; x < xmax; x++) {
      final w = _bilinear((x + xmin - center + 0.5) * ss);
      pre[xx * ksize + x] = w;
      ww += w;
    }
    for (var x = 0; x < xmax; x++) {
      if (ww != 0.0) pre[xx * ksize + x] /= ww;
    }
    bounds[xx * 2] = xmin;
    bounds[xx * 2 + 1] = xmax;
  }
  final kk = Int32List(outSize * ksize);
  for (var i = 0; i < kk.length; i++) {
    final v = pre[i] * (1 << _precisionBits);
    kk[i] = (v < 0 ? -0.5 + v : 0.5 + v).toInt();
  }
  return _Coeffs(ksize, bounds, kk);
}

int _clip8(int v) => math.max(0, math.min(255, v >> _precisionBits));

/// Pillow Image.resize(size, BILINEAR) for an RGB image (Pillow 13.0).
///
/// Two passes, each rounded to 8 bits. Like Pillow 13, the vertical pass runs first when the height
/// shrinks by more than twice as many pixels as the width; otherwise the horizontal pass runs first.
/// The order changes the rounding, so it must match Pillow's for the output to be byte-identical.
RgbImage resizeBilinear(RgbImage img, int outW, int outH) {
  if (outW == img.width && outH == img.height) {
    return RgbImage(outW, outH, Uint8List.fromList(img.pixels));
  }
  final shrinkH = img.height - outH, shrinkW = img.width - outW;
  final verticalFirst = shrinkH > 0 && shrinkH > shrinkW * 2;
  var cur = img;
  if (verticalFirst) {
    if (outH != cur.height) cur = _resizeVertical(cur, outH);
    if (outW != cur.width) cur = _resizeHorizontal(cur, outW);
  } else {
    if (outW != cur.width) cur = _resizeHorizontal(cur, outW);
    if (outH != cur.height) cur = _resizeVertical(cur, outH);
  }
  return cur;
}

RgbImage _resizeHorizontal(RgbImage cur, int outW) {
  final half = 1 << (_precisionBits - 1);
  final c = _precompute(cur.width, outW);
  final out = Uint8List(outW * cur.height * 3);
  for (var y = 0; y < cur.height; y++) {
    final row = y * cur.width * 3;
    for (var xx = 0; xx < outW; xx++) {
      final xmin = c.bounds[xx * 2], n = c.bounds[xx * 2 + 1], k = xx * c.ksize;
      var s0 = half, s1 = half, s2 = half;
      for (var x = 0; x < n; x++) {
        final p = row + (x + xmin) * 3, w = c.kk[k + x];
        s0 += cur.pixels[p] * w;
        s1 += cur.pixels[p + 1] * w;
        s2 += cur.pixels[p + 2] * w;
      }
      final o = (y * outW + xx) * 3;
      out[o] = _clip8(s0);
      out[o + 1] = _clip8(s1);
      out[o + 2] = _clip8(s2);
    }
  }
  return RgbImage(outW, cur.height, out);
}

RgbImage _resizeVertical(RgbImage cur, int outH) {
  final half = 1 << (_precisionBits - 1);
  final c = _precompute(cur.height, outH);
  final out = Uint8List(cur.width * outH * 3);
  for (var yy = 0; yy < outH; yy++) {
    final ymin = c.bounds[yy * 2], n = c.bounds[yy * 2 + 1], k = yy * c.ksize;
    for (var x = 0; x < cur.width; x++) {
      var s0 = half, s1 = half, s2 = half;
      for (var y = 0; y < n; y++) {
        final p = ((y + ymin) * cur.width + x) * 3, w = c.kk[k + y];
        s0 += cur.pixels[p] * w;
        s1 += cur.pixels[p + 1] * w;
        s2 += cur.pixels[p + 2] * w;
      }
      final o = (yy * cur.width + x) * 3;
      out[o] = _clip8(s0);
      out[o + 1] = _clip8(s1);
      out[o + 2] = _clip8(s2);
    }
  }
  return RgbImage(cur.width, outH, out);
}

/// NCHW float32 (1, 3, H, W) scaled to [0, 1]; no mean/std normalisation.
Float32List toTensor(RgbImage img) {
  final plane = img.width * img.height;
  final t = Float32List(3 * plane);
  for (var i = 0; i < plane; i++) {
    t[i] = img.pixels[i * 3] / 255.0;
    t[plane + i] = img.pixels[i * 3 + 1] / 255.0;
    t[2 * plane + i] = img.pixels[i * 3 + 2] / 255.0;
  }
  return t;
}

/// Smallest photo side accepted. Below about 10 px wide, Pillow's resize was seen to differ from this
/// port (Pillow 12.3); no camera produces such images, so they are rejected outright.
const int minSide = 32;

class PhotoTooSmall implements Exception {
  PhotoTooSmall(this.width, this.height);
  final int width, height;
  @override
  String toString() => 'Photo is ${width}x$height; each side must be at least $minSide px';
}

/// Full contract: orientation first, then resize to [size] x [size] (the model's input size from its
/// manifest; the contract default is 640), then tensor.
Float32List preprocess(RgbImage img, {int orientation = 1, int size = inputSize}) {
  if (img.width < minSide || img.height < minSide) throw PhotoTooSmall(img.width, img.height);
  return toTensor(resizeBilinear(applyExifOrientation(img, orientation), size, size));
}
