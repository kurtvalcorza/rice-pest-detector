# Contract: the notebook generator and its `--check`

`tools/build_notebook.py` writes the training notebooks in `notebooks/` from the package source and the files in `data/`. The notebooks are build products: they are never edited by hand (README, "Training notebooks"; constitution, Principle III).

## Command line

```text
python tools/build_notebook.py --revision <base-model revision> [--variant r18|r50|r50v5|dfine-l|rfdetr-m] [--check]
```

| Variant | Output | Base model | Revision used | `transformers` | Settings | Drive run folder |
| :-- | :-- | :-- | :-- | :-- | :-- | :-- |
| `r18` (default) | `train_colab.ipynb` | `PekingU/rtdetr_r18vd` | `ac77a11f…` | 4.57.6 | defaults (batch 8, 60 epochs) | `run-r18` |
| `r50` | `train_colab_r50.ipynb` | `PekingU/rtdetr_r50vd` | `df939e66…` | 4.57.6 | batch 4, 40 epochs | `run-r50` |
| `r50v5` | `train_colab_r50v5.ipynb` | `PekingU/rtdetr_r50vd` | `df939e66…` | 5.20.1 | batch 4, 40 epochs | `run-r50v5` |
| `dfine-l` | `train_colab_dfine-l.ipynb` | `ustc-community/dfine-large-coco` | `aa8f8211…` | 5.20.1 | batch 4, 40 epochs | `run-dfine-l` |
| `rfdetr-m` | `train_colab_rfdetr-m.ipynb` | `Roboflow/rf-detr-medium` | `1b5b6724…` | 5.20.1 | batch 4, 40 epochs, input 576 | `run-rfdetr-m` |

The full revisions are in the README's model badges and in each notebook's `fit` cell.

- Without `--check`: writes the notebook and prints its path.
- With `--check`: builds into `runs/check.ipynb`, compares it byte for byte with the committed notebook and exits 0 if they are identical, 1 otherwise. It never changes the committed file.

## The 24 cells, in order

| Cell id | Content |
| :-- | :-- |
| `intro` | Markdown title and how to run |
| `drive` | Mount Google Drive (after r18, only if not already mounted), make the run folder, warn below 20 GB free |
| `env` | `nvidia-smi`; `pip install transformers==<pin> pycocotools scipy` |
| `versions` | Print versions; raise if no GPU |
| `env-log` | Write `env-<UTC>.txt` (Python, torch, CUDA, transformers, `nvidia-smi`, `pip freeze`) to the run folder |
| `dirs` | Make `/content/rpd/rice_pest_detector` and `/content/rpd/data` |
| `module-00` … `module-09` | `%%writefile` of each `src/rice_pest_detector/*.py`, sorted by name |
| `data-00` … `data-04` | Each `data/*.json`, sorted, as gzip + base64, decoded to `/content/rpd/data/` |
| `fetch` | Reuse a verified archive, else a verified Drive copy, else download; extract and verify every image |
| `fit` | `TrainConfig(base_model=..., revision=...<settings>)`; `fit(...)` |
| `test-eval` | The locked test look ([evaluation-reporting.md](evaluation-reporting.md)); at `input_size` for non-640 models |

## Byte-reproducibility rules

- Fixed cell ids; no outputs; notebook metadata `accelerator: GPU`, `colab.gpuType: T4`.
- gzip with `mtime=0`, compression level 9 and the OS byte forced to 255, so the embedded data is identical on every platform.
- Files written with `newline="\n"`; `.gitattributes` marks `*.ipynb -text` and `data/*.json` as LF, because a CRLF checkout of `data/` had made `--check` fail.
- The r18 notebook stays byte-identical to the one that ran r18-1, so it keeps two behaviours later variants changed: a fixed 0.5 test threshold and an unconditional `drive.mount`.
- The dataset credit is added to the intro of variants built after it was introduced; the five existing variants were run before, so they are built without it to keep `--check` passing (`BUILT_BEFORE_CREDIT`).

A consequence: the notebooks embed the current `src/` and `data/`. A change to any package module or data file makes every `--check` fail until the notebooks are rebuilt, which is intended: a committed notebook always runs the committed code.

## Tests and checks

- `tests/test_build_notebook.py` (on fresh builds in a temporary folder): every module embedded and the revision pinned; no outputs or tokens; small and deterministic; embedded data decodes to the original bytes; the test cell guards against re-evaluation; the GPU stop; the fetch and env-log cells; the Drive space warning; each variant's model, run folder, batch, `transformers` pin and input size; r18 unchanged by the variant option; the dataset credit for new variants.
- The committed notebooks: all five matched a fresh build on 2026-10-19. CI does not yet run the five `--check` commands (open task T073; see the plan's Complexity Tracking).
