# Contract: evaluation results, quality gates and how they are reported

What an evaluation computes (`src/rice_pest_detector/train.evaluate`, `metrics.py`), which gates it is judged against, and the rules for writing results into `docs/evaluation-record.md`. Principle IV of the constitution applies throughout.

## What `evaluate(model, dataset, coco_gt, threshold)` returns

| Key | Meaning |
| :-- | :-- |
| `map50_species` | AP at IoU 0.50 with sexes merged into RBB and WSB; pycocotools with `maxDets = [1, 10, 300]`; uses every detection (threshold 0.0), so it measures ranking |
| `map50_by_class` | Four-class AP50 (`all`) and per class `RBB_FEMALE`, `RBB_MALE`, `WSB_FEMALE`, `WSB_MALE` |
| `threshold` | The counting threshold used for everything below |
| `count_accuracy` | Share of photos where each species' count is within ±10% of the truth, or ±1 when the truth is under 10 |
| `count_accuracy_no_detection_baseline` | The same with every count set to 0 (validation 0.474, test 0.456) |
| `count_errors` | Per species: `mae`, `bias` (negative = undercount), `exact`, `presence_recall`, `mae_by_density` for 1–9, 10–29 and 30+ insects |
| `detections_kept` | Detections at or above the threshold, over all photos |
| `top_score_per_image` | p50, p90 and max of each photo's highest score |
| `confusion` | `truth->prediction` counts at IoU 0.5, including `missed` and `spurious` |

The evaluator asserts that annotation image `i` is manifest record `i`, so labels and detections cannot be misaligned. `EVALUATOR_VERSION = 2`; it is bumped whenever `evaluate` changes what it measures.

## Gates

| Gate | Bar | Judged on | Source of the bar |
| :-- | :-- | :-- | :-- |
| Species mAP50 | ≥ 0.80 | Test, once (rule C) | README, "Status and release gates" |
| Count accuracy | ≥ 0.80 of photos, beside the baseline | Test, once; ≥ 0.80 out-of-fold on validation to earn the look (rule C) | Same |
| Each sex class mAP50 | ≥ 0.70 to expose sexes | Test | Same |
| ONNX size | ≤ 200 MB | The exported file | Rule D |
| ONNX ↔ PyTorch parity | Same kept detections and classes, box IoU ≥ 0.99, score difference ≤ 1e-3 | 10 validation photos at the counting threshold | Rule D |
| CPU latency | ≤ 5 s per photo, median of 10 | Reference laptop | Rule D |

Model choice between candidates uses rules A and B (out-of-fold validation count accuracy plus the dense-tray paired bootstrap: 18 validation photos with 30+ white stemborers, 10,000 resamples, seed 20261017, 95% interval entirely below 0). The release gates beyond these (field validation, wording, data protection, phone latency) are held outside this feature.

## The test look

1. The threshold, calibration and model are fixed on validation first; in every notebook after r18 the test cell has `THRESHOLD = None` and raises until a validation-chosen value is typed in (the r18 notebook, kept byte-identical to the one that ran, uses a fixed 0.5).
2. `evaluation_id` binds the result to `best_pt_sha256`, `manifest_sha256`, `annotations_sha256`, `threshold` and `evaluator_version`; the result is written atomically to `test_metrics.json` with that identity.
3. If `test_metrics.json` exists, `check_cached_test` compares identities (before printing anything, in every notebook after r18) and raises on any change ("protocol violation, stop and ask the owner"); a matching cache is shown instead of evaluating again.
4. Each look is recorded with its date, rule and threshold. As the README and the evaluation record state: the test split has had both its rule-based looks (r18-1 on 13 Oct, r50-v5 on 18 Oct), plus a post-hoc comparison of the two challengers by owner exception, which was not used to choose a model. A later model needs a new held-out set.

## Reporting rules (`docs/evaluation-record.md`)

- Every result names its run, split, date, command and the file it came from (for example `runs/run-r50v5/test_metrics.json`), and its label: built, CPU-tested or hosted-executed.
- Count accuracy is never shown without the baseline; validation counts are out-of-fold (5 family-grouped folds) whenever a threshold was chosen on the same photos.
- Rules are written into the record, dated, before the results they govern, and then applied in the record ("Pre-registered rules, applied").
- Limits found after the fact are recorded, not fixed silently: the threshold grid edge, the parity tolerance waiver, the change from order-based to paired parity.
- Owner decisions not about models go to `docs/decisions.md`.
- Numbers in the README, model cards and decks are copied from the record, not recomputed.

## Tests

`tests/test_metrics.py` (tolerance, species grouping, every species must pass, confusion, mAP grouping, count errors), `tests/test_train.py` (`evaluate` reports errors, baseline and scores; refuses a mismatched COCO file; the cached test result is bound to the whole evaluation), `tests/test_choose_demo_threshold.py`, `tests/test_calibrate_scores.py`, `tests/test_build_notebook.py` (the test cell waits for a threshold and checks the protocol before showing cached numbers).
