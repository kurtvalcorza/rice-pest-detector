import 'package:flutter/material.dart';

import '../l10n/app_localizations.dart';

class AboutScreen extends StatelessWidget {
  const AboutScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final l = AppLocalizations.of(context);
    return Scaffold(
      appBar: AppBar(title: Text(l.about)),
      body: ListView(padding: const EdgeInsets.all(16), children: [
        Text(l.intendedUse),
        const SizedBox(height: 16),
        Text(l.privacyNotice),
        const SizedBox(height: 16),
        Text(l.licences, style: Theme.of(context).textTheme.bodySmall),
        const SizedBox(height: 16),
        OutlinedButton(
            onPressed: () => showLicensePage(context: context, applicationName: l.appTitle),
            child: Text(l.openSourceLicences)),
      ]),
    );
  }
}
