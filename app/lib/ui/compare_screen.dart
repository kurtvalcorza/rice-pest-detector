// Counts one photo with every installed model, one model at a time (each is loaded, run and freed before
// the next, to bound memory), and shows the counts, review flags and time side by side. Clearly a
// comparison of demo models; nothing is saved to history and nothing leaves the phone.
import 'dart:async';

import 'package:flutter/material.dart';

import '../app/services.dart';
import '../counting/counting.dart';
import '../inference/decode.dart';
import '../inference/detector.dart';
import '../inference/preprocess.dart';
import '../l10n/app_localizations.dart';
import '../model/model_registry.dart';
import 'not_validated_banner.dart';
import 'settings_screen.dart' show ModelTags, modelDetails;

class _Row {
  _Row(this.model, {this.count, this.elapsed});
  final InstalledModel model;
  final PhotoCount? count;
  final Duration? elapsed;
}

class CompareScreen extends StatefulWidget {
  const CompareScreen({super.key, required this.services, required this.models});
  final AppServices services;
  final List<InstalledModel> models;

  @override
  State<CompareScreen> createState() => _CompareScreenState();
}

class _CompareScreenState extends State<CompareScreen> {
  final _rows = <_Row>[];
  (int, String)? _running;

  /// The photo being compared. It is a private copy made by the photo picker and no history entry points to
  /// it, so it is deleted when the next comparison starts or the screen closes.
  PhotoRef? _photo;

  void _discardPhoto() {
    final photo = _photo;
    _photo = null;
    if (photo != null) unawaited(s.photos.discard(photo));
  }

  @override
  void dispose() {
    _discardPhoto();
    super.dispose();
  }

  AppServices get s => widget.services;

  Future<void> _compare(Future<PhotoRef?> Function() pick) async {
    final l = AppLocalizations.of(context);
    final messenger = ScaffoldMessenger.of(context);
    final photo = await pick();
    if (photo == null) return;
    if (!mounted) {
      // The screen closed while the camera or gallery was open: delete the copy nothing will show.
      await s.photos.discard(photo);
      return;
    }
    _discardPhoto();
    _photo = photo;
    setState(_rows.clear);
    for (var i = 0; i < widget.models.length; i++) {
      final m = widget.models[i];
      setState(() => _running = (i + 1, m.label));
      // The active model's detector is already loaded: reuse it rather than load a second copy.
      final reuse = m.id == s.activeModel?.id ? s.detector : null;
      Detector? opened;
      try {
        final detector = reuse ?? (opened = await s.models!.open(m));
        final watch = Stopwatch()..start();
        final dets = await detector.detect(photo);
        watch.stop();
        final count = countPhoto(photo.name, dets, threshold: m.threshold, reviewBelow: m.reviewBelow);
        if (mounted) setState(() => _rows.add(_Row(m, count: count, elapsed: watch.elapsed)));
      } on PhotoTooSmall {
        messenger.showSnackBar(SnackBar(content: Text(l.photoTooSmall)));
        break;
      } on PhotoTooLarge {
        messenger.showSnackBar(SnackBar(content: Text(l.photoTooLarge)));
        break;
      } on PhotoUnreadable {
        messenger.showSnackBar(SnackBar(content: Text(l.photoUnreadable)));
        break;
      } catch (_) {
        if (mounted) setState(() => _rows.add(_Row(m)));
      } finally {
        if (opened != null) await s.models!.close(opened);
      }
      if (!mounted) return;
    }
    if (mounted) setState(() => _running = null);
  }

  @override
  Widget build(BuildContext context) {
    final l = AppLocalizations.of(context);
    final text = Theme.of(context).textTheme;
    final reasonText = {ReviewReason.lowConfidence: l.reviewLowConfidence, ReviewReason.crowded: l.reviewCrowded};
    final running = _running;
    return Scaffold(
      appBar: AppBar(title: Text(l.compareTitle)),
      body: ListView(padding: const EdgeInsets.all(16), children: [
        const NotValidatedBanner(),
        const SizedBox(height: 8),
        Text(l.compareNotice),
        const SizedBox(height: 16),
        if (running != null)
          Row(children: [
            const CircularProgressIndicator(),
            const SizedBox(width: 16),
            Expanded(child: Text(l.compareProgress(running.$1, widget.models.length, running.$2))),
          ])
        else ...[
          FilledButton.icon(
              onPressed: s.models == null ? null : () => _compare(s.photos.camera),
              icon: const Icon(Icons.photo_camera),
              label: Text(l.takePhoto)),
          const SizedBox(height: 8),
          OutlinedButton.icon(
              onPressed: s.models == null ? null : () => _compare(s.photos.gallery),
              icon: const Icon(Icons.photo_library),
              label: Text(l.choosePhoto)),
        ],
        const SizedBox(height: 16),
        for (final r in _rows)
          Card(
            child: Padding(
              padding: const EdgeInsets.all(12),
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Text(r.model.label, style: text.titleMedium),
                Text(modelDetails(l, r.model), style: text.bodySmall),
                const SizedBox(height: 4),
                ModelTags(model: r.model),
                const SizedBox(height: 8),
                if (r.count == null)
                  Text(l.compareFailed)
                else ...[
                  for (final code in speciesCodes)
                    Row(children: [
                      Expanded(child: Text(code == 'RBB' ? l.speciesRBB : l.speciesWSB)),
                      Text('${r.count!.counts[code]}', key: Key('compare-${r.model.id}-$code'),
                          style: text.titleLarge),
                    ]),
                  const SizedBox(height: 4),
                  Text(
                      r.count!.reasons.isEmpty
                          ? l.compareNoFlags
                          : [for (final x in r.count!.reasons) reasonText[x]!].join('\n'),
                      key: Key('compare-${r.model.id}-flags')),
                  Text(l.compareTime((r.elapsed!.inMicroseconds / 1e6).toStringAsFixed(1)),
                      key: Key('compare-${r.model.id}-time'), style: text.bodySmall),
                ],
              ]),
            ),
          ),
      ]),
    );
  }
}
