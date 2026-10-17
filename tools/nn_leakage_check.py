"""Report, for each val/test family, the Hamming distance to its nearest train family (dHash).

Usage: python -m tools.nn_leakage_check --dataset-root <riceprotek-insects-v28/datasets> [--manifest data/split_manifest.json]

Uses the same representative rule as the split (`manifest._representative`) so the numbers describe
the images the split actually compared. Read-only: nothing is written to the dataset.
"""

import argparse
import json
from collections import defaultdict
from pathlib import Path

import numpy as np
from PIL import Image

from rice_pest_detector.dedup import dhash
from rice_pest_detector.manifest import DEDUP_MAX_DISTANCE, _is_grey, _representative

THRESHOLDS = (2, 4)


def representative_hashes(manifest: dict, root: Path) -> dict[str, tuple[str, int]]:
    """family -> (split, dHash of the family's representative image)."""
    by_family: dict[str, list[dict]] = defaultdict(list)
    for rec in manifest["images"]:
        by_family[rec["family"]].append(rec)
    out: dict[str, tuple[str, int]] = {}
    for family, recs in by_family.items():
        items = []
        for rec in recs:
            path = root / rec["relative_path"]
            with Image.open(path) as img:
                items.append({"path": path, "origin": rec["origin_split"], "grey": _is_grey(img)})
        pick, _ = _representative(items)
        with Image.open(pick["path"]) as img:
            out[family] = (recs[0]["split"], dhash(img))
    return out


def nearest_train_distances(hashes: dict[str, tuple[str, int]]) -> dict[str, dict[str, int]]:
    train = np.array([h for s, h in hashes.values() if s == "train"], dtype=np.uint64)
    result: dict[str, dict[str, int]] = {"val": {}, "test": {}}
    for family, (split, h) in sorted(hashes.items()):
        if split == "train":
            continue
        xor = train ^ np.uint64(h)
        dist = np.unpackbits(xor.view(np.uint8).reshape(-1, 8), axis=1).sum(axis=1)
        result[split][family] = int(dist.min())
    return result


def summarize(distances: dict[str, dict[str, int]]) -> dict:
    summary = {}
    for split, per_family in distances.items():
        values = sorted(per_family.values())
        summary[split] = {"families": len(values), "min_distance": values[0] if values else None,
                          **{f"within_d{t}": sum(v <= t for v in values) for t in THRESHOLDS}}
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset-root", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, default=Path("data/split_manifest.json"))
    args = parser.parse_args()
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    distances = nearest_train_distances(representative_hashes(manifest, args.dataset_root))
    print(json.dumps({"dedup_max_distance": DEDUP_MAX_DISTANCE, **summarize(distances)}, indent=1))


if __name__ == "__main__":
    main()