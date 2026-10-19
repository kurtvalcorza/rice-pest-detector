# Data Model: Desktop Trap Pest Counter

**Feature**: [spec.md](spec.md) | **Plan**: [plan.md](plan.md)

The desktop reuses the phone app's data unchanged (FR-009, Principle VII). Only **Settings** is new. All files live in the per-user application-support folder (research R5): `models/` (with `models/active.json`), `model/` (the pinned default model's download), `photos/`, `history/history.json` and `settings.json`. The phone's developer side-load folder `demo/` is not used on the desktop.

## Model (existing: `InstalledModel`, `ModelManifest`)

| Field | Type | Rule |
| :-- | :-- | :-- |
| `id` | string | Unique per installed model; folder name under `models/` |
| `label`, `architecture` | string | From the manifest |
| `input_size` | int | Square, 320–1280 |
| `threshold` | number | Count a detection when `score >= threshold` (inclusive) |
| `review_below` | number | Flag the photo when a kept detection scores below this |
| `sha256`, `bytes` | string, int | Must match the file before the model is used (Principle VI) |
| `validation` | object | `count_accuracy`, `species_map50`, `wsb30_mae` (validation split) |
| `validated` | bool | `false` for every model today |

Manifests are strict: unknown or missing fields are rejected. Exactly one model is the **default** (r50-v5, identified by SHA-256); at most one is **active**.

**State**: `absent` → `downloading` / `importing` → `checking` → `installed` → (`active`) → `deleted`. Any failure in `downloading`, `importing` or `checking` returns to the previous state and removes partial files. The default model cannot be deleted; deleting the active model makes the default active.

## Model catalogue (existing: `app/assets/model_catalog.json`)

A list of published models, each a download URL plus the model's manifest (identical to `models/*.manifest.json`; a test keeps them in sync). Bundled; read-only.

## Count record (existing: `HistoryEntry`, `history/history.json`)

| Field | Type | Rule |
| :-- | :-- | :-- |
| `id` | string | Unique |
| `takenAt` | ISO 8601, UTC | When the count was made |
| `photoPath` | string or null | The app's **copy** of the photo under `photos/` |
| `counts` | map species → int | Rice black bug and white stemborer |
| `reasons` | list of string | Review-flag reasons (low confidence, crowded); empty when none |
| `threshold` | number | The threshold used |
| `modelId` | string | The model used |
| `notValidated` | bool | True when the model was not the default |

Listed newest first. Written through a `.tmp` file and a rename; a corrupt file is renamed to `.corrupt` and a fresh history starts (existing behaviour).

## Settings (new: `settings.json`)

| Field | Type | Rule |
| :-- | :-- | :-- |
| `language` | `"en"`, `"fil"` or absent | Absent means "follow the system": Filipino when the system language is `fil` or `tl`, else English |

The active model stays in the existing `models/active.json`. Written through a `.tmp` file and a rename.

## Parity reference (new: `app/test/fixtures/desktop_parity.json`)

Described in [contracts/parity-fixture.md](contracts/parity-fixture.md). Test data, not app data.
