import 'package:flutter/material.dart';

import '../app/services.dart';
import '../counting/counting.dart';
import '../inference/decode.dart';
import '../inference/detector.dart';
import '../inference/preprocess.dart';
import '../l10n/app_localizations.dart';
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

  AppServices get s => widget.services;

  @override
  void initState() {
    super.initState();
    _reload();
  }

  Future<void> _reload() async {
    final entries = await s.history.load();
    if (mounted) setState(() => _entries = entries);
  }

  Future<void> _download(ModelDownload download) async {
    final l = AppLocalizations.of(context);
    final messenger = ScaffoldMessenger.of(context);
    setState(() => _busy = true);
    try {
      await download.run();
    } catch (_) {
      // Network error, HTTP error, or size/SHA-256 mismatch: nothing was installed.
      if (mounted) setState(() => _busy = false);
      messenger.showSnackBar(SnackBar(content: Text(l.downloadFailed)));
      return;
    }
    if (mounted) setState(() => _busy = false);
    await widget.onModelInstalled?.call();
  }

  Future<void> _analyse(Detector detector, Future<PhotoRef?> Function() pick) async {
    final l = AppLocalizations.of(context);
    final messenger = ScaffoldMessenger.of(context);
    final navigator = Navigator.of(context);
    final photo = await pick();
    if (photo == null) return;
    setState(() => _busy = true);
    try {
      final counted = countPhoto(photo.name, await detector.detect(photo),
          threshold: s.threshold, reviewBelow: s.reviewBelow);
      final entry = HistoryEntry(
          id: s.newId(), takenAt: s.now(), photoPath: photo.path, counts: counted.counts,
          reasons: [for (final r in counted.reasons) r.name], threshold: counted.threshold,
          modelId: detector.modelId, notValidated: s.notValidated);
      await s.history.add(entry);
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
    } finally {
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
            onPressed: () async {
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
            Text(detector == null ? l.downloading : l.analysing),
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
