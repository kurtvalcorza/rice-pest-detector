import 'package:flutter/material.dart';

import '../l10n/app_localizations.dart';

/// Shown wherever a count from a model other than the default appears: home, results, compare.
class NotValidatedBanner extends StatelessWidget {
  const NotValidatedBanner({super.key = const Key('not-validated-banner')});

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    return Card(
      color: scheme.errorContainer,
      child: Padding(
          padding: const EdgeInsets.all(12),
          child: Row(children: [
            Icon(Icons.warning_amber_outlined, color: scheme.onErrorContainer),
            const SizedBox(width: 12),
            Expanded(
                child: Text(AppLocalizations.of(context).notValidatedBanner,
                    style: TextStyle(color: scheme.onErrorContainer))),
          ])),
    );
  }
}
