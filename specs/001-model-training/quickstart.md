# Quickstart: Rice-Pest Model Training

How to check, rebuild and rerun the pipeline. Requirements: Python 3.12 on Windows, macOS or Linux; training also needs a Google Colab session with a T4 GPU. What to install for each task is in `docs/setup.md`. Commands are shown for PowerShell on Windows; on macOS and Linux use `.venv/bin/python`.

## Check it (no dataset, no GPU)

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements.txt   # same as -e ".[dev,train,export]"
.\.venv\Scripts\python -m pytest                            # 142 tests; torch/onnx tests skip without those libraries
.\.venv\Scripts\python -m tools.export_app_fixtures --check # golden fixtures match the reference
.\.venv\Scripts\python app/tool/export_resize_fixtures.py --check
.\.venv\Scripts\python tools/build_notebook.py --revision df939e661d8c52e80608d1ec566561aabd25a4e7 --variant r50v5 --check
```

Each `--check` exits 0 when the committed file equals a fresh build. The other notebooks are checked the same way with their own `--variant` and `--revision` ([contracts/notebook-generator.md](contracts/notebook-generator.md)).

## Rebuild the split (needs the dataset)

Download the dataset archive by its authors (Deleña et al.) from Zenodo (doi:10.5281/zenodo.20066074) and extract it, then:

```powershell
.\.venv\Scripts\python -m rice_pest_detector.manifest --dataset-root <dataset folder>\datasets --out data
.\.venv\Scripts\python -m tools.nn_leakage_check --dataset-root <dataset folder>\datasets
```

The first command prints `{"images": {"train": 4948, "val": 253, "test": 252}, "families": 1684, "groups": 1600, "excluded_families": 1}`, and, with the pinned Pillow and NumPy, `git diff data/` should be empty. The second lists the nearest training neighbour of each validation and test family, for inspection.

## Train (Colab, T4)

1. Open colab.research.google.com in a browser, choose File → Upload notebook and pick, for example, `notebooks/train_colab_r50v5.ipynb`.
2. Set the runtime to a T4 GPU, choose Run all and accept the Drive prompt.
3. After a disconnect, choose Run all again; training resumes from Drive.
4. The last cell stops at the locked test look. Do not set `THRESHOLD` unless a pre-registered rule gives the model the look.
5. Copy `best.pt`, `history.jsonl` and the `env-*.txt` log from Drive `rice-pest-detector/<run folder>/` to `runs/<run folder>/` (not tracked by git).

## Judge it on validation (CPU)

```powershell
.\.venv\Scripts\python -m tools.export_onnx --checkpoint runs/run-r50v5/best.pt --out models/rice-pest-r50-v5.onnx --base-model PekingU/rtdetr_r50vd --revision df939e661d8c52e80608d1ec566561aabd25a4e7
.\.venv\Scripts\python -m tools.choose_demo_threshold --onnx models/rice-pest-r50-v5.onnx --dataset-root <dataset folder> --out runs/run-r50v5/demo_threshold.json
.\.venv\Scripts\python -m tools.calibrate_scores --onnx models/rice-pest-r50-v5.onnx --dataset-root <dataset folder> --out runs/run-r50v5/calibration_val.json --cache runs/run-r50v5/val_dets_onnx.json
```

- For RF-DETR-M add `--size 576` to the export, with its own base model and revision.
- The training checkpoints are not distributed, so these commands need a run of your own (or the published ONNX file for the two validation tools).
- The export writes `models/rice-pest-r50-v5.json` with the file's SHA-256 and size. The published r50-v5 file is 171,744,970 bytes with SHA-256 `dc3927ae0967f6553721e18eec826305cca66c7fb5c8cd1789a8187d74f069c1`; a new export is a new file and needs its own manifest.
- The threshold tool should choose 0.48 for r50-v5.

## Check the export (CPU)

Parity is a function, not a command: call `tools.export_onnx.parity(model, onnx_path, images, threshold)` with the model from `load_trained(...)`, 10 validation photos prepared with `rice_pest_detector.infer.preprocess` and the manifest's threshold. A pass reports 0 failures and the number of detections compared (145 for r50-v5 at 0.48). Time a count as the median of 10 runs per photo on the same laptop as the recorded figures.

## Record it

Write every result into `docs/evaluation-record.md` with its run, split, date, command and source file; write the model's manifest in `models/` ([contracts/model-manifest.md](contracts/model-manifest.md)); then rerun `pytest` and the checks above.
