# Contract: model files

Four JSON formats describe models to the app. The registry and download code reject anything that does not match; field rules are in [data-model.md](../data-model.md).

## 1. Model manifest (`models/*.manifest.json`, and `manifest.json` next to each published `model.onnx`)

Parsed by `ModelManifest.parse` (`app/lib/model/model_manifest.dart`), strictly: 14 required fields, `notes` optional, nothing else.

```json
{
  "id": "r50-v5",
  "label": "r50-v5",
  "architecture": "RT-DETR (ResNet-50)",
  "base_model": "PekingU/rtdetr_r50vd",
  "licence": "Apache-2.0",
  "input_size": 640,
  "threshold": 0.48,
  "review_below": 0.64,
  "sha256": "dc3927ae0967f6553721e18eec826305cca66c7fb5c8cd1789a8187d74f069c1",
  "bytes": 171744970,
  "outputs": ["logits", "pred_boxes"],
  "num_classes": 4,
  "validation": {"count_accuracy": 0.834, "species_map50": 0.937, "wsb30_mae": 8.67},
  "validated": false
}
```

The three published manifests in the repository:

| `id` | `label` | `input_size` | `threshold` | `review_below` | `bytes` | `validation.count_accuracy` |
| :-- | :-- | --: | --: | --: | --: | --: |
| `r50-v5` | r50-v5 | 640 | 0.48 | 0.64 | 171,744,970 | 0.834 |
| `rfdetr-m` | RF-DETR-M | 576 | 0.48 | 0.63 | 121,956,743 | 0.846 |
| `dfine-l` | D-FINE-L | 640 | 0.50 | 0.68 | 125,611,873 | 0.822 |

Validation figures are on the validation split; their provenance is `docs/evaluation-record.md`, "Wave 2".

## 2. Model catalogue (`app/assets/model_catalog.json`)

Parsed by `parsePublishedModels` (`app/lib/model/published_models.dart`).

```json
{"models": [{"url": "https://…/model.onnx", "manifest": { …a model manifest, unchanged… }}]}
```

- The top level has exactly one key, `models`. Each entry has exactly `url` and `manifest`.
- `url` must be `https` with a host. Ids must not repeat.
- Each `manifest` must equal the file in `models/` with the same id (`published_models_test.dart`).
- Bundled and read-only; it is the only source of download URLs in Settings.

## 3. Model pin (`app/assets/model_pin.json`)

Parsed by `ModelPin.fromJson` (`app/lib/model/model_store.dart`). Leniently: missing fields become empty, and an empty pin offers no download.

```json
{"url": "https://…/model.onnx", "sha256": "dc3927ae…f069c1", "bytes": 171744970,
 "threshold": 0.48, "label": "r50-v5", "kind": "demo"}
```

- `kind`: `demo` (the Demo notice) or `published` (default when absent; the release-gated notice). Today `demo`.
- `threshold` absent means the contract default 0.50.
- The pin must equal the default model's catalogue entry (URL, SHA-256, size, threshold, label) (`model_pin_test.dart`).
- The home screen offers "Download the model (172 MB)" when the pin is set and its file is not installed.

## 4. Developer side-load (`demo/demo.json` in app storage)

```json
{"sha256": "…", "bytes": 0, "threshold": 0.48, "label": "…"}
```

Placed by a developer with `adb shell run-as` next to `demo/rice-pest.onnx` (README, "Run it"). The model is used only if the file's size and SHA-256 match. Input size is the contract default, 640.

## Files the app writes

- `models/active.json`: `{"active": "<id>"}`, written through a `.tmp` file and a rename. Unreadable means "no choice".
- `models/<id>/verified.json`: `{"sha256", "bytes", "modified"}` (file modification time in ms). If it matches, start-up skips re-hashing the model.
