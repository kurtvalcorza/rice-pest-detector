import 'package:flutter/material.dart';

import '../app/services.dart';
import '../counting/counting.dart';
import '../inference/decode.dart';
import '../inference/detector.dart';
import '../inference/preprocess.dart';
import '../l10n/app_localizations.dart';
import '../model/model_store.dart';
import '../storage/history.dart';
import 'about_screen.dart';
import 'not_validated_banner.dart';
import 'result_screen.dart';
import 'settings_screen.dart';

class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key, required this.services, this.onModelInstalled});
  final AppServices services;

  /// Called after a verified download, or a model switch in Settings, so the app can restart its
  /// model choice.
  final Future<void> Function()? onModelInstalled;

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  List<HistoryEntry> _entries = [];
  bool _busy = false;

  /// Stops the pinned-model download on Cancel, or when the screen goes away.
  DownloadCancel? _cancel;

  AppServices get s => widget.services;

  @override
  void initState() {
    super.initState();
    _reload();
  }

  @override
  void dispose() {
    _cancel?.cancel();
    super.dispose();
  }

  Future<void> _reload() async {
    final entries = await s.history.load();
    if (mounted) setState(() => _entries = entries);
  }

  Future<void> _download(ModelDownload download) async {
    final l = AppLocalizations.of(context);
    final messenger = ScaffoldMessenger.of(context);
    final cancel = DownloadCancel();
    void idle() {
      if (mounted) {
        setState(() {
          _busy = false;
          _cancel = null;
        });
      }
    }

    setState(() {
      _busy = true;
      _cancel = cancel;
    });
    try {
      await download.run(cancel);
    } on DownloadCancelled {
      idle();
      if (mounted) messenger.showSnackBar(SnackBar(content: Text(l.downloadCancelled)));
      return;
    } catch (_) {
      // Network error, timeout, HTTP error, or size/SHA-256 mismatch: nothing was installed.
      idle();
      messenger.showSnackBar(SnackBar(content: Text(l.downloadFailed)));
      return;
    }
    idle();
    await widget.onModelInstalled?.call();
  }

  Future<void> _analyse(Detector detector, Future<PhotoRef?> Function() pick) async {
    final l = AppLocalizations.of(context);
    final messenger = ScaffoldMessenger.of(context);
    final navigator = Navigator.of(context);
    final photo = await pick();
    if (photo == null) return;
    if (!mounted) {
      // The screen went away while the camera or gallery was open: nothing will own the copy.
      await s.photos.discard(photo);
      return;
    }
    // Set once the history entry that points to the photo is saved; until then a failure deletes the copy.
    var kept = false;
    setState(() => _busy = true);
    try {
      final counted = countPhoto(photo.name, await detector.detect(photo),
          threshold: s.threshold, reviewBelow: s.reviewBelow);
      final entry = HistoryEntry(
          id: s.newId(), takenAt: s.now(), photoPath: photo.path, counts: counted.counts,
          reasons: [for (final r in counted.reasons) r.name], threshold: counted.threshold,
          modelId: detector.modelId, notValidated: s.notValidated);
      await s.history.add(entry);
      kept = true;
      if (!mounted) return;
      setState(() => _busy = false);
      await navigator.push(MaterialPageRoute(builder: (_) => ResultScreen(entry: entry, services: s)));
      await _reload();
    } on PhotoTooSmall {
      messenger.showSnackBar(SnackBar(content: Text(l.photoTooSmall)));
    } on PhotoTooLarge {
      messenger.showSnackBar(SnackBar(content: Text(l.photoTooLarge)));
    } on PhotoUnreadable {
      messenger.showSnackBar(SnackBar(content: Text(l.photoUnreadable)));
    } catch (_) {
      // Once the entry is saved, a later error (showing the result) is not a failed count.
      if (kept) rethrow;
      // The model or the history store failed: nothing was counted or saved, and the copy is deleted below.
      messenger.showSnackBar(SnackBar(content: Text(l.analysisFailed)));
    } finally {
      if (!kept) await s.photos.discard(photo);
      if (mounted && _busy) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final l = AppLocalizations.of(context);
    final detector = s.detector;
    return Scaffold(
      appBar: AppBar(title: Text(l.appTitle), actions: [
        IconButton(
            tooltip: l.settings,
            icon: const Icon(Icons.settings_outlined),
            // Not while counting or downloading: switching model in Settings would replace the detector
            // this screen is using.
            onPressed: _busy
                ? null
                : () async {
              await Navigator.of(context).push(MaterialPageRoute(
                  builder: (_) => SettingsScreen(services: s, onModelChanged: widget.onModelInstalled)));
              await _reload();
            }),
        IconButton(
            tooltip: l.about,
            icon: const Icon(Icons.info_outline),
            onPressed: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => const AboutScreen()))),
      ]),
      body: ListView(padding: const EdgeInsets.all(16), children: [
        _Notice(text: switch (s.mode) { ModelMode.none => l.noModelNotice, ModelMode.demo => l.demoNotice, ModelMode.published => l.modelNotice }),
        if (s.notValidated) ...[const SizedBox(height: 8), const NotValidatedBanner()],
        const SizedBox(height: 16),
        if (_busy)
          Row(children: [
            const CircularProgressIndicator(),
            const SizedBox(width: 16),
            Expanded(child: Text(detector == null ? l.downloading : l.analysing)),
            if (_cancel != null) TextButton(onPressed: _cancel!.cancel, child: Text(l.cancelDownload)),
          ])
        else ...[
          if (detector == null && s.download != null) ...[
            FilledButton.icon(
                onPressed: () => _download(s.download!),
                icon: const Icon(Icons.download),
                label: Text(l.downloadModel((s.download!.bytes / 1e6).round()))),
            const SizedBox(height: 16),
          ],
          FilledButton.icon(
              onPressed: detector == null ? null : () => _analyse(detector, s.photos.camera),
              icon: const Icon(Icons.photo_camera),
              label: Text(l.takePhoto)),
          const SizedBox(height: 8),
          OutlinedButton.icon(
              onPressed: detector == null ? null : () => _analyse(detector, s.photos.gallery),
              icon: const Icon(Icons.photo_library),
              label: Text(l.choosePhoto)),
        ],
        const SizedBox(height: 24),
        Text(l.history, style: Theme.of(context).textTheme.titleMedium),
        if (_entries.isEmpty) Padding(padding: const EdgeInsets.only(top: 8), child: Text(l.noHistory)),
        for (final e in _entries)
          ListTile(
            title: Text(formatTakenAt(e.takenAt)),
            subtitle: Text('${l.speciesRBB}: ${e.counts['RBB']}  ·  ${l.speciesWSB}: ${e.counts['WSB']}'),
            trailing: e.reasons.isEmpty ? null : const Icon(Icons.flag_outlined),
            onTap: () async {
              await Navigator.of(context)
                  .push(MaterialPageRoute(builder: (_) => ResultScreen(entry: e, services: s)));
              await _reload();
            },
          ),
      ]),
    );
  }
}

class _Notice extends StatelessWidget {
  const _Notice({required this.text});
  final String text;

  @override
  Widget build(BuildContext context) => Card(
        color: Theme.of(context).colorScheme.tertiaryContainer,
        child: Padding(
            padding: const EdgeInsets.all(12),
            child: Row(children: [
              const Icon(Icons.science_outlined),
              const SizedBox(width: 12),
              Expanded(child: Text(text)),
            ])),
      );
}
