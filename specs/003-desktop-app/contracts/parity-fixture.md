# Contract: desktop parity fixture (SC-001)

`tools/export_desktop_parity.py` writes `app/test/fixtures/desktop_parity.json`. Producing the expected counts needs the photos and the three models, which are not in the repository, so the tool has two modes:

- **Export** (maintainer, with photos and models): writes the whole file.
- **`--check`** (CI, no photos or models needed): writes nothing and exits 1 if the photo list or its SHA-256s in the file differ from what the selection rule and `data/split_manifest.json` give, or if any photo lacks an entry for a published model in the catalogue.

## Photo choice

20 photos from the **validation** split recorded in `data/split_manifest.json` (never test; validation already holds one image per family), chosen by `random.Random(20261019).sample(sorted(validation_file_names), 20)`. The rule, not the list, is the source of truth; the list is written into the file for readers.

## File format

```json
{
  "generated_by": "tools/export_desktop_parity.py",
  "split": "validation",
  "seed": 20261019,
  "photos": [
    {
      "file": "<dataset file name>",
      "sha256": "<photo SHA-256>",
      "expected": {
        "<model id>": {
          "counts": {"rice_black_bug": 0, "white_stemborer": 0},
          "reasons": []
        }
      }
    }
  ]
}
```

- One `expected` entry per published model (r50-v5, RF-DETR-M, D-FINE-L), produced by `rice_pest_detector.infer` with ONNX Runtime and each model's manifest threshold and review level.
- `sha256` lets the integration test confirm it has the same photo before comparing.

## Use

`app/integration_test/desktop_parity_test.dart` reads the file, looks for the photos in a folder given by `RPD_PARITY_PHOTOS` and the models in the app's data folder, and compares counts and reasons exactly for every pair. It is skipped, with a message, when the photos or a model are missing.
