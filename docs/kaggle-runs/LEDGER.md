# Kaggle runs: ledger

Append-only record of the Kaggle editions' verification runs and publication receipts (spec 010). Rows are never edited; a correction is a new row. Each row's evidence is in `docs/kaggle-runs/<variant>/`.

**Coverage.** CI builds every notebook and checks it against the committed file, and runs the unit tests; these are static checks, not execution evidence. Kaggle runs are manual and recorded below.

**Baseline before the Kaggle editions (2026-10-20).** `python -m pytest -q`: exit 0, 141 passed, 1 skipped. `tools/build_notebook.py --check` exit 0 for each of the five Colab notebooks, whose SHA-256 values are:

| Notebook | SHA-256 |
| :-- | :-- |
| `notebooks/train_colab.ipynb` | `22bde1f00eed5dd831f935cf2ce49e6c94ad95f2875d4178c66bde220cb15f5f` |
| `notebooks/train_colab_r50.ipynb` | `d16847486d7b827b6635314f4c03dde266bced47759c13746511d38353bf160e` |
| `notebooks/train_colab_r50v5.ipynb` | `99f6711dea50eece1a4fc16393070914bac1ddf5684b01bc1fa64aa761b7c98c` |
| `notebooks/train_colab_dfine-l.ipynb` | `663ba2052e67f7ea6a5a1b438f261d3a1ce49d038cc45b1476cd784bc58295df` |
| `notebooks/train_colab_rfdetr-m.ipynb` | `267b287d2a71cd7a779a3463c8cb594707c6a4e5519c3bdfaa87d978d0f0880d` |

**Verdicts.** `VERIFIED`: the run's source and lock match the declaration, the GPU was a T4, the recomputed numbers equal the printed ones and each is within its tolerance of the evaluation record (or the owner has ruled on it). `DIFFERS`: everything matches but a number is outside its tolerance; the owner rules and the run is not repeated. `FAILED`: a source, lock, GPU, output, hash or recomputation check failed. `PUBLIC`: the owner made the edition public and an anonymous check saw it. `SAVED (no run)`: a new version saved without running (Kaggle Quick Save) to change metadata such as the model link or tags; the verified run stays in the version history.

| Date (UTC) | Edition | Kaggle version | Code commit | Source hash | GPU | Time | Verdict | Evidence |
| :-- | :-- | :-- | :-- | :-- | :-- | :-- | :-- | :-- |
| 2026-10-21 | r50v5-kaggle | 2 | debb28d | 4e9658084386… | Tesla T4 | 6.8 h | VERIFIED | r50v5/r50v5-v2-verification.json |
| 2026-10-21 | r50v5-kaggle | 2 | debb28d | 4e9658084386… | - | - | PUBLIC | r50v5/receipt.json |
| 2026-10-21 | rfdetr-m-kaggle | 1 | debb28d | 780d5fec729e… | Tesla T4 | 5.7 h | VERIFIED | rfdetr-m/rfdetr-m-v1-verification.json |
| 2026-10-21 | rfdetr-m-kaggle | 1 | debb28d | 780d5fec729e… | - | - | PUBLIC | rfdetr-m/receipt.json |
| 2026-10-21 | r50v5-kaggle | 3 | 7a2d240 | 0710e8e53f77… | - | - | SAVED (no run) | model link; Kaggle dropped 4 of 5 tags, see version 4 |
| 2026-10-21 | rfdetr-m-kaggle | 2 | 7a2d240 | abbce7ebe9c1… | - | - | SAVED (no run) | model link and tags |
| 2026-10-21 | r50v5-kaggle | 4 | 7a2d240 | 0710e8e53f77… | - | - | SAVED (no run) | model link and tags |
