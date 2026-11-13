"""Paired bootstrap of per-photo white-stemborer count errors on crowded trays.

The prospectively documented rules compare two models on the 18 validation photos with 30 or more white
stemborers: the new model counts as better only if the 95% interval of the mean paired difference
lies entirely below 0. Run: python -m tools.dense_tray_bootstrap runs/<run>/dense_wsb_bootstrap*.json
recomputes a saved report and exits 1 if its interval does not match.
"""

import argparse
import json
import sys
from pathlib import Path

import numpy as np

RESAMPLES = 10_000
SEED = 20261017


def paired_bootstrap(ref_err, new_err, resamples: int = RESAMPLES, seed: int = SEED) -> dict:
    """Interval of the mean of new_err - ref_err; lower is better for the new model."""
    ref, new = np.asarray(ref_err, dtype=np.float64), np.asarray(new_err, dtype=np.float64)
    if ref.size == 0 or ref.shape != new.shape:
        raise ValueError("the two error lists must cover the same photos, in the same order")
    diff = new - ref
    picks = np.random.default_rng(seed).integers(0, diff.size, size=(resamples, diff.size))
    low, high = np.percentile(diff[picks].mean(axis=1), [2.5, 97.5])
    return {"mean_diff": float(diff.mean()), "ci95": [float(low), float(high)], "new_is_better": bool(high < 0),
            "resamples": resamples, "seed": seed}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("report", type=Path, help="a saved dense_wsb_bootstrap*.json")
    args = ap.parse_args(argv)
    saved = json.loads(args.report.read_text(encoding="utf-8"))
    ref = saved.get("ref_abs_err", saved.get("r18_abs_err"))  # the first report named its two models
    new = saved.get("new_abs_err", saved.get("r50_abs_err"))
    result = paired_bootstrap(ref, new, saved["resamples"], saved["seed"])
    same = bool(np.allclose(result["ci95"], saved["ci95"]))
    print(f"mean difference {result['mean_diff']:.2f}, 95% interval [{result['ci95'][0]:.2f}, {result['ci95'][1]:.2f}]: "
          f"{'matches the saved report' if same else 'DIFFERS from the saved ' + str(saved['ci95'])}")
    return 0 if same else 1


if __name__ == "__main__":
    sys.exit(main())
