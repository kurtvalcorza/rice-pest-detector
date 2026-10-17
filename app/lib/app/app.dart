import 'package:flutter/material.dart';

import '../l10n/app_localizations.dart';
import '../ui/home_screen.dart';
import 'services.dart';

class RicePestApp extends StatefulWidget {
  const RicePestApp({super.key, required this.services, this.locale, this.reload});

  final AppServices services;

  /// Null follows the phone's language (Filipino or English; English otherwise).
  final Locale? locale;

  /// Re-runs the start-up model choice; called after a verified model download and after the model is
  /// switched or deleted in Settings. Throws if the chosen model cannot be loaded.
  final Future<AppServices> Function()? reload;

  @override
  State<RicePestApp> createState() => _RicePestAppState();
}

class _RicePestAppState extends State<RicePestApp> {
  late AppServices _services = widget.services;

  Future<void> _reloadModel() async {
    final reload = widget.reload;
    if (reload == null) return;
    final previous = _services;
    final next = await reload();
    if (mounted) setState(() => _services = next);
    // The new model is loaded before the old one is freed, so a failed load leaves the app working.
    await previous.release?.call();
  }

  @override
  Widget build(BuildContext context) => MaterialApp(
        onGenerateTitle: (c) => AppLocalizations.of(c).appTitle,
        theme: ThemeData(colorSchemeSeed: const Color(0xFF2E7D32), useMaterial3: true),
        localizationsDelegates: AppLocalizations.localizationsDelegates,
        supportedLocales: AppLocalizations.supportedLocales,
        locale: widget.locale,
        // A new key per services object rebuilds the home screen in the new mode.
        home: HomeScreen(key: ObjectKey(_services), services: _services, onModelInstalled: _reloadModel),
      );
}
