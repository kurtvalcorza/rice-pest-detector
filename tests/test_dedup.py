import numpy as np
from PIL import Image

from rice_pest_detector.dedup import dhash, group_families


def _gradient(seed: int) -> Image.Image:
    rng = np.random.default_rng(seed)
    return Image.fromarray(rng.integers(0, 255, (64, 64, 3), dtype=np.uint8))


def test_dhash_is_stable_and_64_bit():
    img = _gradient(1)
    assert dhash(img) == dhash(img.copy())
    assert 0 <= dhash(img) < 2**64


def test_dhash_tolerates_recompression_scale():
    img = _gradient(2)
    smaller = img.resize((48, 48))
    assert bin(dhash(img) ^ dhash(smaller)).count("1") <= 6


def test_group_families_merges_transitively_and_keeps_singletons():
    hashes = {"a": [0b0000], "b": [0b0011], "c": [0b1111], "d": [2**64 - 1]}
    groups = group_families(hashes, max_distance=2)
    assert frozenset({"a", "b", "c"}) in groups
    assert frozenset({"d"}) in groups
    assert sorted(f for g in groups for f in g) == ["a", "b", "c", "d"]
