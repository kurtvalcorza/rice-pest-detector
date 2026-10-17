import 'package:flutter/material.dart';

import '../app/services.dart';
import '../counting/counting.dart';
import '../l10n/app_localizations.dart';
import '../storage/history.dart';
import 'not_validated_banner.dart';

class ResultScreen extends StatelessWidget {
  const ResultScreen({super.key, required this.entry, required this.services});
  final HistoryEntry entry;
  final AppServices services;

  @override
  Widget build(BuildContext context) {
    final l = AppLocalizations.of(context);
    final threshold = entry.threshold.toStringAsFixed(2);
    final names = {'RBB': l.speciesRBB, 'WSB': l.speciesWSB};
    final reasonText = {
      ReviewReason.lowConfidence.name: l.reviewLowConfidence,
      ReviewReason.crowded.name: l.reviewCrowded,
    };
    final text = Theme.of(context).textTheme;
    return Scaffold(
      appBar: AppBar(title: Text('${l.resultTitle} · ${formatTakenAt(entry.takenAt)}')),
      body: ListView(padding: const EdgeInsets.all(16), children: [
        if (entry.notValidated) const NotValidatedBanner(),
        for (final code in speciesCodes)
          ListTile(
            title: Text(names[code]!),
            trailing: Text('${entry.counts[code]}', key: Key('count-$code'), style: text.headlineMedium),
          ),
        if (entry.reasons.isNotEmpty) ...[
          const SizedBox(height: 8),
          ListTile(
            leading: const Icon(Icons.flag_outlined),
            title: Text(l.needsReview),
            subtitle: Text([for (final r in entry.reasons) reasonText[r] ?? r].join('\n')),
          ),
        ],
        const SizedBox(height: 16),
        Text(l.modelNotice),
        const SizedBox(height: 8),
        Text(l.modelInfo(entry.modelId, threshold), style: text.bodySmall),
        const SizedBox(height: 24),
        FilledButton.icon(
          icon: const Icon(Icons.share),
          label: Text(l.shareCounts),
          onPressed: () {
            final summary = l.shareSummary(formatTakenAt(entry.takenAt), entry.counts['RBB']!,
                entry.counts['WSB']!, entry.modelId, threshold);
            // A count from a non-default model carries the banner wherever it goes.
            services.sharer.share(entry.notValidated ? '${l.notValidatedBanner} $summary' : summary,
                photoPath: entry.photoPath);
          },
        ),
      ]),
    );
  }
}
