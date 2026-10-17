"""Perceptual (dHash) duplicate screening across image families."""

import numpy as np
from PIL import Image


def dhash(image: Image.Image) -> int:
    small = np.asarray(image.convert("L").resize((9, 8), Image.Resampling.BILINEAR), dtype=np.int16)
    bits = (small[:, 1:] > small[:, :-1]).flatten()
    return int("".join("1" if b else "0" for b in bits), 2)


def _popcount(x: np.ndarray) -> np.ndarray:
    return np.unpackbits(x.view(np.uint8).reshape(-1, 8), axis=1).sum(axis=1)


def group_families(hashes: dict[str, list[int]], max_distance: int = 4) -> list[frozenset[str]]:
    families = sorted(hashes)
    owner = np.array([i for i, f in enumerate(families) for _ in hashes[f]], dtype=np.int64)
    values = np.array([h for f in families for h in hashes[f]], dtype=np.uint64)
    parent = list(range(len(families)))

    def find(i: int) -> int:
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    for k in range(len(values)):
        close = np.nonzero(_popcount(values ^ values[k]) <= max_distance)[0]
        for j in close:
            ra, rb = find(int(owner[k])), find(int(owner[j]))
            if ra != rb:
                parent[rb] = ra
    groups: dict[int, set[str]] = {}
    for i, f in enumerate(families):
        groups.setdefault(find(i), set()).add(f)
    return [frozenset(g) for g in groups.values()]
