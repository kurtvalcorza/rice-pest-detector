// Settings → Model: every installed model with its facts, tap to use it; import a model from files on
// the phone or download a published one (both verified before they are enabled, never made active
// automatically); delete imported models; open the compare screen.
import 'package:flutter/material.dart';

import '../app/services.dart';
import '../l10n/app_localizations.dart';
import '../model/model_manifest.dart' show doNothingCountAccuracy;
import '../model/model_registry.dart';
import '../model/model_store.dart';
import '../model/published_models.dart';
import 'compare_screen.dart';

class SettingsScreen extends StatefulWidget {
  const SettingsScreen({super.key, required this.services, this.onModelChanged});
  final AppServices services;

  /// Re-runs the start-up model choice (RicePestApp's reload); throws if the model cannot be loaded.
  final Future<void> Function()? onModelChanged;

  @override
  State<SettingsScreen> createState() => _SettingsScreenState();
}

class _SettingsScreenState extends State<SettingsScreen> {
  List<InstalledModel> _models = [];
  bool _busy = false;
  String? _busyText;

  /// The published model being downloaded, its progress, and how to stop it.
  String? _downloadingId;
  int _received = 0;
  int? _total;
  DownloadCancel? _cancel;

  AppServices get s => widget.services;
  String? get _activeId => s.activeModel?.id;
  bool get _idle => !_busy && _downloadingId == null;

  /// Installed means a model with the same SHA-256 is on the phone, whatever its id.
  bool _installed(PublishedModel p) => _models.any((m) => m.sha256 == p.manifest.sha256);
  bool _inUse(PublishedModel p) => s.activeModel?.sha256 == p.manifest.sha256;

  @override
  void dispose() {
    _cancel?.cancel();
    super.dispose();
  }

  @override
  void initState() {
    super.initState();
    _refresh();
  }

  Future<void> _refresh() async {
    final models = await s.models?.list() ?? const <InstalledModel>[];
    if (mounted) setState(() => _models = models);
  }

  void _say(ScaffoldMessengerState messenger, String text) =>
      messenger..hideCurrentSnackBar()..showSnackBar(SnackBar(content: Text(text)));

  /// A failed model check's message plus its reason (e.g. the ONNX Runtime error), so a failure on a phone
  /// can be diagnosed from a screenshot. Long reasons are cut.
  static String _withDetail(AppLocalizations l, String message, ModelImportFailed e) {
    final detail = e.detail.trim();
    if (detail.isEmpty) return message;
    return l.errorWithDetail(message, detail.length <= 200 ? detail : '${detail.substring(0, 199)}…');
  }

  Future<void> _use(InstalledModel m) async {
    final catalog = s.models;
    if (catalog == null || m.id == _activeId) return;
    final l = AppLocalizations.of(context);
    final messenger = ScaffoldMessenger.of(context);
    final navigator = Navigator.of(context);
    final previous = _activeId;
    setState(() => _busy = true);
    try {
      await catalog.activate(m.id);
      await widget.onModelChanged?.call();
    } catch (_) {
      // Loading failed: restore the previous choice so the next start-up does not pick the broken model.
      await catalog.activate(previous);
      if (mounted) setState(() => _busy = false);
      _say(messenger, l.switchFailed);
      return;
    }
    navigator.popUntil((r) => r.isFirst);
    _say(messenger, l.switchedModel(m.label));
  }

  Future<void> _delete(InstalledModel m) async {
    final catalog = s.models;
    if (catalog == null) return;
    final l = AppLocalizations.of(context);
    final ok = await showDialog<bool>(
        context: context,
        builder: (c) => AlertDialog(
              title: Text(l.deleteModel),
              content: Text(l.deleteModelConfirm(m.label)),
              actions: [
                TextButton(onPressed: () => Navigator.of(c).pop(false), child: Text(l.cancel)),
                TextButton(onPressed: () => Navigator.of(c).pop(true), child: Text(l.deleteEntry)),
              ],
            ));
    if (ok != true || !mounted) return;
    final wasActive = m.id == _activeId;
    final navigator = Navigator.of(context);
    await catalog.delete(m.id);
    if (wasActive) {
      // The registry cleared the choice, so the reload falls back to the default model.
      await widget.onModelChanged?.call();
      navigator.popUntil((r) => r.isFirst);
      return;
    }
    await _refresh();
  }

  Future<void> _import() async {
    final catalog = s.models, files = s.modelFiles;
    if (catalog == null || files == null) return;
    final l = AppLocalizations.of(context);
    final messenger = ScaffoldMessenger.of(context);
    _say(messenger, l.importPickManifest);
    // The screen can be left while a file picker is open: stop then rather than update a closed screen.
    final manifest = await files.pickManifest();
    if (manifest == null || !mounted) return;
    _say(messenger, l.importPickModel);
    final model = await files.pickModel();
    if (model == null || !mounted) return;
    messenger.hideCurrentSnackBar();
    setState(() {
      _busy = true;
      _busyText = l.importChecking;
    });
    try {
      final m = await catalog.importFrom(model: model, manifest: manifest);
      _say(messenger, l.importDone(m.label));
    } on ModelImportFailed catch (e) {
      _say(messenger, switch (e.reason) {
        ImportFailure.manifestInvalid => l.importErrorManifest,
        ImportFailure.sizeMismatch => l.importErrorSize,
        ImportFailure.checksumMismatch => l.importErrorChecksum,
        ImportFailure.shapeMismatch => _withDetail(l, l.importErrorShape, e),
        ImportFailure.selfTestFailed => _withDetail(l, l.importErrorSelfTest, e),
        ImportFailure.alreadyInstalled => l.importErrorExists,
        ImportFailure.unreadable => l.importErrorFile,
      });
    } catch (_) {
      _say(messenger, l.importErrorFile);
    } finally {
      if (mounted) {
        setState(() {
          _busy = false;
          _busyText = null;
        });
      }
    }
    await _refresh();
  }

  /// Downloads a published model (only ever on this tap) and installs it with the import checks. The
  /// active model is not changed; the user taps the new model to use it.
  Future<void> _download(PublishedModel p) async {
    final catalog = s.models;
    if (catalog == null || !_idle) return;
    final l = AppLocalizations.of(context);
    final messenger = ScaffoldMessenger.of(context);
    final cancel = DownloadCancel();
    setState(() {
      _downloadingId = p.manifest.id;
      _received = 0;
      _total = null;
      _cancel = cancel;
    });
    try {
      final m = await catalog.download(p, cancel: cancel, onProgress: (received, total) {
        // Redraw about every 0.1 MB, not on every network chunk.
        if (!mounted || (received - _received < 100000 && received != total && total == _total)) return;
        setState(() {
          _received = received;
          _total = total;
        });
      });
      _say(messenger, l.downloadDone(m.label));
    } on DownloadCancelled {
      _say(messenger, l.downloadCancelled);
    } on ModelDownloadFailed {
      _say(messenger, l.downloadErrorNetwork);
    } on ModelImportFailed catch (e) {
      _say(messenger, switch (e.reason) {
        ImportFailure.sizeMismatch => l.downloadErrorSize,
        ImportFailure.checksumMismatch => l.downloadErrorChecksum,
        ImportFailure.alreadyInstalled => l.importErrorExists,
        _ => _withDetail(l, l.downloadErrorCheck, e),
      });
    } catch (_) {
      _say(messenger, l.downloadErrorCheck);
    } finally {
      if (mounted) {
        setState(() {
          _downloadingId = null;
          _cancel = null;
        });
      }
    }
    await _refresh();
  }

  @override
  Widget build(BuildContext context) {
    final l = AppLocalizations.of(context);
    final text = Theme.of(context).textTheme;
    final published = s.models?.published ?? const <PublishedModel>[];
    return Scaffold(
      appBar: AppBar(title: Text(l.settings)),
      body: ListView(padding: const EdgeInsets.all(16), children: [
        Text(l.modelSection, style: text.titleMedium),
        const SizedBox(height: 4),
        Text(l.modelListHint, style: text.bodySmall),
        const SizedBox(height: 8),
        if (_models.isEmpty)
          Padding(padding: const EdgeInsets.symmetric(vertical: 8), child: Text(l.noModelsInstalled)),
        for (final m in _models) _ModelTile(model: m, active: m.id == _activeId, enabled: _idle,
            onTap: () => _use(m), onDelete: m.deletable ? () => _delete(m) : null),
        if (published.isNotEmpty) ...[
          const SizedBox(height: 16),
          Text(l.downloadSection, style: text.titleMedium),
          const SizedBox(height: 4),
          Text(l.downloadHint, style: text.bodySmall),
          const SizedBox(height: 8),
          for (final p in published)
            _PublishedTile(
                model: p,
                installed: _installed(p),
                inUse: _inUse(p),
                downloading: _downloadingId == p.manifest.id,
                received: _received,
                total: _total,
                enabled: _idle,
                onDownload: () => _download(p),
                onCancel: () => _cancel?.cancel()),
        ],
        const SizedBox(height: 16),
        if (_busy)
          Row(children: [
            const CircularProgressIndicator(),
            if (_busyText != null) ...[const SizedBox(width: 16), Expanded(child: Text(_busyText!))],
          ])
        else ...[
          OutlinedButton.icon(
              onPressed: s.models == null || s.modelFiles == null || !_idle ? null : _import,
              icon: const Icon(Icons.file_open_outlined),
              label: Text(l.importModel)),
          const SizedBox(height: 8),
          OutlinedButton.icon(
              onPressed: _models.isEmpty
                  ? null
                  : () => Navigator.of(context)
                      .push(MaterialPageRoute(builder: (_) => CompareScreen(services: s, models: _models))),
              icon: const Icon(Icons.compare_outlined),
              label: Text(l.compareModels)),
        ],
      ]),
    );
  }
}

/// Facts shown for a model: architecture, input size, counting threshold, validation count accuracy beside
/// the do-nothing baseline.
String modelDetails(AppLocalizations l, InstalledModel m) => l.modelDetails(
    m.architecture.isEmpty ? '—' : m.architecture, m.inputSize, m.threshold.toStringAsFixed(2),
    m.validation == null ? '—' : m.validation!.countAccuracy.toStringAsFixed(3),
    doNothingCountAccuracy.toStringAsFixed(3));

class ModelTags extends StatelessWidget {
  const ModelTags({super.key, required this.model, this.active = false});
  final InstalledModel model;
  final bool active;

  @override
  Widget build(BuildContext context) {
    final l = AppLocalizations.of(context);
    Widget tag(String t, Color c) => Container(
        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
        decoration: BoxDecoration(color: c, borderRadius: BorderRadius.circular(8)),
        child: Text(t, style: Theme.of(context).textTheme.labelSmall));
    final scheme = Theme.of(context).colorScheme;
    return Wrap(spacing: 6, runSpacing: 4, children: [
      if (model.isDefault) tag(l.defaultTag, scheme.primaryContainer),
      if (active) tag(l.activeTag, scheme.secondaryContainer),
      if (!model.validated) tag(l.notValidatedTag, scheme.errorContainer),
    ]);
  }
}

/// One published model: its facts and download size, then a Download button, "Installed" (and "In use"),
/// or the progress of its download with a cancel button.
class _PublishedTile extends StatelessWidget {
  const _PublishedTile({required this.model, required this.installed, required this.inUse,
      required this.downloading, required this.received, required this.total, required this.enabled,
      required this.onDownload, required this.onCancel});
  final PublishedModel model;
  final bool installed;
  final bool inUse;
  final bool downloading;
  final int received;
  final int? total;
  final bool enabled;
  final VoidCallback onDownload;
  final VoidCallback onCancel;

  static String _mb(int bytes) => (bytes / 1e6).toStringAsFixed(1);

  @override
  Widget build(BuildContext context) {
    final l = AppLocalizations.of(context);
    final theme = Theme.of(context);
    final m = model.manifest;
    Widget tag(String t, Color c) => Container(
        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
        decoration: BoxDecoration(color: c, borderRadius: BorderRadius.circular(8)),
        child: Text(t, style: theme.textTheme.labelSmall));
    final Widget? trailing = installed
        ? Wrap(spacing: 6, children: [
            tag(l.installedTag, theme.colorScheme.primaryContainer),
            if (inUse) tag(l.activeTag, theme.colorScheme.secondaryContainer),
          ])
        : downloading
            ? null
            : FilledButton(onPressed: enabled ? onDownload : null, child: Text(l.download));
    final t = total;
    return Card(
      key: Key('published-${m.id}'),
      child: Padding(
        padding: const EdgeInsets.fromLTRB(16, 12, 16, 12),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Row(children: [
            Expanded(child: Text(m.label, style: theme.textTheme.titleMedium)),
            ?trailing,
          ]),
          const SizedBox(height: 4),
          Text(l.publishedDetails(m.architecture, m.inputSize, m.threshold.toStringAsFixed(2),
              m.validation.countAccuracy.toStringAsFixed(3), doNothingCountAccuracy.toStringAsFixed(3),
              (m.bytes / 1e6).round())),
          if (downloading) ...[
            const SizedBox(height: 8),
            LinearProgressIndicator(value: t == null || t <= 0 ? null : (received / t).clamp(0.0, 1.0)),
            Row(children: [
              Expanded(
                  child: Text(t == null ? l.downloadProgressUnknown(_mb(received)) : l.downloadProgress(_mb(received), _mb(t)))),
              TextButton(onPressed: onCancel, child: Text(l.cancelDownload)),
            ]),
          ],
        ]),
      ),
    );
  }
}

class _ModelTile extends StatelessWidget {
  const _ModelTile({required this.model, required this.active, required this.enabled, required this.onTap,
      this.onDelete});
  final InstalledModel model;
  final bool active;
  final bool enabled;
  final VoidCallback onTap;
  final VoidCallback? onDelete;

  @override
  Widget build(BuildContext context) {
    final l = AppLocalizations.of(context);
    return Card(
      key: Key('model-${model.id}'),
      child: ListTile(
        enabled: enabled,
        selected: active,
        leading: Icon(active ? Icons.radio_button_checked : Icons.radio_button_unchecked),
        title: Text(model.label),
        subtitle: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text(modelDetails(l, model)),
          const SizedBox(height: 4),
          ModelTags(model: model, active: active),
        ]),
        isThreeLine: true,
        trailing: onDelete == null
            ? null
            : IconButton(
                tooltip: l.deleteModel,
                icon: const Icon(Icons.delete_outline),
                onPressed: enabled ? onDelete : null),
        onTap: onTap,
      ),
    );
  }
}
