# Contract: split manifest and annotation files

`python -m rice_pest_detector.manifest --dataset-root <dataset folder>/datasets --out data` writes four files to `data/`. They are committed, read by the notebooks (embedded), the evaluation tools and the tests, and never edited by hand. Line endings are LF (`.gitattributes`), because the notebook generator embeds them byte for byte.

## `split_manifest.json`

```json
{
  "seed": 20261013,
  "images": [
    {
      "file": "<dataset file name>",
      "relative_path": "02_detection_dataset/<origin>/images/<file>",
      "archive_member": "datasets/02_detection_dataset/<origin>/images/<file>",
      "family": "<lower-case stem>",
      "group": "grp00000",
      "split": "train | val | test",
      "origin_split": "train | valid | test",
      "selection_rule": "null | published-original | first-colour | first-any",
      "sha256": "<64 hex>",
      "bytes": 117416,
      "width": 640,
      "height": 640,
      "boxes": [[2, 0.2305, 0.3484, 0.0656, 0.0445]]
    }
  ]
}
```

- `images` is sorted by family, then by the family's variants; train holds every variant, val and test one image per family.
- `boxes` rows are `[class_id, cx, cy, w, h]`, normalised to [0, 1]; class ids 0–3 are `RBB_FEMALE`, `RBB_MALE`, `WSB_FEMALE`, `WSB_MALE`.
- Written with `json.dumps(..., indent=1)`.

## `annotations_{train,val,test}.json`

COCO detection JSON, one file per split, images in the same order as the split's records in the manifest, `id` from 1. Boxes are converted to pixels as `[(cx − w/2)·W, (cy − h/2)·H, w·W, h·H]`; `category_id` is `class_id + 1`; `iscrowd` is 0. Written compact (no indent).

## `exclusions.json`

A list of `{"family": ..., "reason": ...}`; a family is excluded whole when any member has no label file, a malformed row (not 5 fields and not an odd polygon row of 7 or more), a class outside 0–3, a non-finite coordinate, a non-positive area or a box outside the image (tolerance 1e-6).

## Build rules (what the files guarantee)

1. Families from file names (`families.family_key`); polygon rows become min/max boxes (`labels.parse_labels`).
2. One representative per family by the evaluation-variant rule; dHash of the representative; families within distance 1 form a group (`dedup.group_families`, `manifest.DEDUP_MAX_DISTANCE`).
3. Each group gets a stratum (`rbb`, `wsb` or `mixed`, from its boxes); within each stratum the sorted groups are shuffled with `random.Random(20261013)` and the first 15% go to val, the next 15% to test, the rest to train (`split.split_groups`).
4. A tray with more than 300 boxes stops the build (`num_queries`).

## Checks

- `tests/test_committed_split.py` (reads the committed files): no family, group or file SHA-256 in two splits; sizes 4,948 / 253 / 252 and seed 20261013; one image per family in val and test; each annotation file lists exactly its split's images.
- `tests/test_manifest.py`, `test_split.py`, `test_dedup.py`, `test_families.py`, `test_labels.py` (synthetic data): leakage, variant choice, exclusions with reasons, the 300-box limit, COCO categories from 1, hashing of representatives only.
- In the notebook: `fetch.extract_members` refuses any image whose SHA-256 differs from `sha256`, any `relative_path` that escapes the output folder, and names a missing archive member.

Consumers: the training notebooks, `tools/choose_demo_threshold.py`, `tools/calibrate_scores.py`, `tools/compare_base_vs_finetuned.py`, `tools/nn_leakage_check.py`.
