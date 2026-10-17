// Count history kept in app-private storage as one JSON file (photos stay on the phone).
// JSON rather than SQLite: one user's history is tens to hundreds of entries, and this needs no
// native plugin and is testable on the host. Writes go through a .tmp file and a rename.
import 'dart:convert';
import 'dart:io';

class HistoryEntry {
  HistoryEntry({required this.id, required this.takenAt, required this.photoPath, required this.counts,
      required this.reasons, required this.threshold, required this.modelId, this.notValidated = false});

  factory HistoryEntry.fromJson(Map<String, dynamic> j) => HistoryEntry(
        id: j['id'] as String,
        takenAt: DateTime.parse(j['takenAt'] as String),
        photoPath: j['photoPath'] as String?,
        counts: (j['counts'] as Map<String, dynamic>).map((k, v) => MapEntry(k, v as int)),
        reasons: (j['reasons'] as List).cast<String>(),
        threshold: (j['threshold'] as num).toDouble(),
        modelId: j['modelId'] as String,
        notValidated: j['notValidated'] as bool? ?? false,
      );

  final String id;
  final DateTime takenAt;
  final String? photoPath;
  final Map<String, int> counts;
  final List<String> reasons;
  final double threshold;
  final String modelId;

  /// Counted with a model that is not the default: the result and anything shared carry the
  /// "Demo model, not validated" banner. Entries written before this field read as false.
  final bool notValidated;

  Map<String, dynamic> toJson() => {
        'id': id, 'takenAt': takenAt.toUtc().toIso8601String(), 'photoPath': photoPath,
        'counts': counts, 'reasons': reasons, 'threshold': threshold, 'modelId': modelId,
        'notValidated': notValidated,
      };
}

abstract class History {
  Future<List<HistoryEntry>> load();
  Future<void> add(HistoryEntry entry);
  Future<void> delete(String id);
}

class HistoryStore implements History {
  HistoryStore(this.dir);
  final Directory dir;

  File get _file => File('${dir.path}${Platform.pathSeparator}history.json');

  @override
  Future<List<HistoryEntry>> load() async {
    if (!await _file.exists()) return [];
    try {
      final data = jsonDecode(await _file.readAsString()) as List;
      final entries = [for (final e in data) HistoryEntry.fromJson(e as Map<String, dynamic>)];
      return entries..sort((a, b) => b.takenAt.compareTo(a.takenAt));
    } on FormatException {
      await _file.rename('${_file.path}.corrupt'); // keep it for support; start a fresh history
      return [];
    } on TypeError {
      await _file.rename('${_file.path}.corrupt');
      return [];
    }
  }

  @override
  Future<void> add(HistoryEntry entry) async => _save([entry, ...await load()]);

  @override
  Future<void> delete(String id) async {
    final all = await load();
    for (final e in all.where((e) => e.id == id)) {
      final p = e.photoPath;
      if (p != null && await File(p).exists()) await File(p).delete();
    }
    await _save([for (final e in all) if (e.id != id) e]);
  }

  Future<void> _save(List<HistoryEntry> entries) async {
    await dir.create(recursive: true);
    final tmp = File('${_file.path}.tmp');
    await tmp.writeAsString(jsonEncode([for (final e in entries) e.toJson()]), flush: true);
    await tmp.rename(_file.path);
  }
}
