# Data Model: Trap Pest Counter (phone app)

**Feature**: [spec.md](spec.md) | **Plan**: [plan.md](plan.md)

Everything lives in the app's documents folder (`getApplicationDocumentsDirectory()`, which only the app can read on Android), set up in `app/lib/main.dart`. File formats are in [contracts/model-files.md](contracts/model-files.md).

## Storage layout

```text
<documents>/
├── models/                     # the model registry (ModelRegistry)
│   ├── <id>/model.onnx
│   ├── <id>/manifest.json
│   ├── <id>/verified.json      # {sha256, bytes, modified}: skip re-hashing at start-up
│   ├── active.json             # {"active": "<id>"}; absent = no choice (use the default)
│   ├── .import-<id>/           # staging during an import or download (dot: never listed)
│   └── .download-<id>.part     # a catalogue download in progress
├── model/rice-pest.onnx        # the pinned download (ModelStore); .part while downloading
├── demo/rice-pest.onnx         # developer side-load ...
├── demo/demo.json              # ... with {sha256, bytes, threshold, label}
├── history/history.json        # count records (+ .tmp while writing, .corrupt if unreadable)
└── photos/trap-<ms>.<ext>      # the app's copies of counted (and compared) photos
```

## Model manifest (`ModelManifest`, `app/lib/model/model_manifest.dart`)

| Field | Type | Rule |
| :-- | :-- | :-- |
| `id` | string | 1–64 chars: lower-case letters, digits, `.`, `_`, `-`; first char a letter or digit; also the folder name |
| `label`, `architecture`, `base_model`, `licence` | string | `label` not blank |
| `input_size` | int | Square side, 320–1280 |
| `threshold` | number | Strictly between 0 and 1, above the detector floor 0.02; count when `score >= threshold` |
| `review_below` | number | Strictly between 0 and 1, not under `threshold`; flag the photo when a counted detection scores below it |
| `sha256` | string | 64 lower-case hex digits |
| `bytes` | int | Positive |
| `outputs` | list | Exactly `["logits", "pred_boxes"]` |
| `num_classes` | int | Exactly 4 |
| `validation` | object | Exactly `count_accuracy` (0–1), `species_map50` (0–1), `wsb30_mae` (≥ 0) |
| `validated` | bool | `false` for all three published models |
| `notes` | string | Optional |

Unknown or missing fields are rejected. A manifest file over 64 KB is not read.

## Installed model (`InstalledModel`, `app/lib/model/model_registry.dart`)

What the app knows about a usable model, from any of three sources:

| Source (`ModelSource`) | Where | Facts available |
| :-- | :-- | :-- |
| `registry` | `models/<id>/` | Everything in the manifest |
| `pin` | `model/rice-pest.onnx` | Label, SHA-256, threshold from the pin; input size 640; review level 0.64; no validation figures |
| `sideloaded` | `demo/` | Label, SHA-256, threshold from `demo.json`; input size 640; review level 0.64 |

Derived: `isDefault` (SHA-256 equals r50-v5's), `deletable` (registry source and not the default).

**Listing**: registry models first, then the pin and side-load if their id and SHA-256 are not already listed; sorted default first, then by label. A registry folder is listed only if its manifest parses, its id matches the folder name, the file size matches and the SHA-256 matches (or a matching `verified.json` stamp exists).

**State transitions**:

```text
absent ──download / import──▶ staged ──size, SHA-256, session check──▶ installed ──tap──▶ active
   ▲                            │ any failure: staging deleted              │ delete (not default)
   └────────────────────────────┘                                          ▼
                                                                  absent (active cleared → default)
```

## Start-up model choice (`chooseModel`, `app/lib/app/bootstrap.dart`)

In order: the model named in `active.json`, if installed; else the default model (by SHA-256); else the pinned model; else the side-loaded model; else none. A non-default model is used only when it was made active.

| Mode (`ModelMode`) | When | Notice |
| :-- | :-- | :-- |
| `none` | No model chosen | "No model is installed yet…"; download offered if the pin is set |
| `demo` | The chosen model is neither a `published` pin nor `validated` | "Demo: real model weights…not validated in the field" |
| `published` | A pin of kind `published`, or a model with `validated: true` | "Experimental model. Counts are estimates…" |

Today every route ends in `demo` (the pin's kind is `demo`; every manifest says `validated: false`).

## Count record (`HistoryEntry`, `app/lib/storage/history.dart`)

| Field | Type | Rule |
| :-- | :-- | :-- |
| `id` | string | Unique (microseconds since epoch by default) |
| `takenAt` | ISO 8601 string, UTC | When the count was made; shown in local time as `YYYY-MM-DD HH:MM` |
| `photoPath` | string or null | The app's copy under `photos/` |
| `counts` | map | `{"RBB": int, "WSB": int}` |
| `reasons` | list of string | `lowConfidence`, `crowded`; empty when none |
| `threshold` | number | The threshold used |
| `modelId` | string | The model's label |
| `notValidated` | bool | True when the model was not the default; entries without it read as `false` |

Loaded newest first. Written whole through `history.json.tmp` and a rename. A file that fails to parse is renamed to `history.json.corrupt` and an empty history is returned. Deleting an entry also deletes its photo copy (`HistoryStore.delete`; no screen calls it yet).

## Photo count (in memory: `PhotoCount`, `app/lib/counting/counting.dart`)

Counts per species over detections with `score >= threshold`; reasons `lowConfidence` (any counted score `< review_below`) and `crowded` (more than 30 counted). Not stored except through a count record.
