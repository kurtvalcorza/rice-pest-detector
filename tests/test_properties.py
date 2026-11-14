"""Property-based tests (Hypothesis) for the small, deterministic pieces the release gates rest on.

Each test states a property that must hold for every input, not just the examples in the
other test files: the leakage-free family grouping, the split proportions, the count
tolerance, and the ordering and threshold behaviour of post-processing.
"""

from collections import Counter
from fractions import Fraction

import numpy as np
import pytest
from hypothesis import example, given, settings
from hypothesis import strategies as st

from rice_pest_detector import SPECIES_OF_CLASS
from rice_pest_detector.dedup import group_families
from rice_pest_detector.infer import postprocess
from rice_pest_detector.metrics import (
    count_accuracy,
    count_errors,
    count_within_tolerance,
)
from rice_pest_detector.split import split_groups

SPECIES = ("RBB", "WSB")

# --- dedup.group_families -------------------------------------------------------------------


def _hamming(a: int, b: int) -> int:
    return (a ^ b).bit_count()


@st.composite
def clustered_hashes(draw):
    """Families of 64-bit hashes drawn near a few shared bases, so close pairs actually occur."""
    bases = draw(st.lists(st.integers(0, 2**64 - 1), min_size=1, max_size=4))
    n_families = draw(st.integers(1, 8))
    hashes = {}
    for i in range(n_families):
        values = []
        for _ in range(draw(st.integers(1, 3))):
            h = draw(st.sampled_from(bases))
            for bit in draw(st.lists(st.integers(0, 63), max_size=8)):
                h ^= 1 << bit
            values.append(h)
        hashes[f"f{i}"] = values
    return hashes


def _close(hashes: dict[str, list[int]], a: str, b: str, max_distance: int) -> bool:
    return any(_hamming(x, y) <= max_distance for x in hashes[a] for y in hashes[b])


@given(clustered_hashes(), st.integers(0, 8))
def test_group_families_is_a_partition(hashes, max_distance):
    groups = group_families(hashes, max_distance)
    assert all(groups)
    assert sum(len(g) for g in groups) == len(hashes)
    assert set().union(*groups) == set(hashes)


@given(clustered_hashes(), st.integers(0, 8))
def test_group_families_never_separates_near_duplicates(hashes, max_distance):
    """No leakage: two families with any hashes within max_distance share a group."""
    group_of = {f: i for i, g in enumerate(group_families(hashes, max_distance)) for f in g}
    for a in hashes:
        for b in hashes:
            if _close(hashes, a, b, max_distance):
                assert group_of[a] == group_of[b]


@given(clustered_hashes(), st.integers(0, 8))
def test_group_families_only_merges_connected_families(hashes, max_distance):
    """Groups are the connected components of the near-duplicate graph, not coarser."""
    for group in group_families(hashes, max_distance):
        start = next(iter(group))
        seen, frontier = {start}, [start]
        while frontier:
            a = frontier.pop()
            for b in group - seen:
                if _close(hashes, a, b, max_distance):
                    seen.add(b)
                    frontier.append(b)
        assert seen == group


@given(clustered_hashes(), st.integers(0, 7))
def test_group_families_coarsens_as_max_distance_grows(hashes, max_distance):
    fine = group_families(hashes, max_distance)
    coarse = group_families(hashes, max_distance + 1)
    assert all(any(g <= c for c in coarse) for g in fine)


@given(st.integers(0, 2**64 - 1), st.integers(1, 8), st.integers(2, 6), st.randoms(use_true_random=False))
def test_group_families_merges_a_chain_of_near_duplicates(start, max_distance, length, rnd):
    """Each family is exactly max_distance bits from the previous one, so the first and last are
    far apart: only a transitive merge (a working union-find) puts them in one group."""
    chain, h = [], start
    for _ in range(length):
        chain.append(h)
        for bit in rnd.sample(range(64), max_distance):
            h ^= 1 << bit
    # group_families works in sorted name order, so the names, not the dict order, decide the order
    # in which links are found; a permutation makes some links join trees that are already merged.
    names = rnd.sample(range(length), length)
    hashes = {f"f{names[i]}": [v] for i, v in enumerate(chain)}
    assert group_families(hashes, max_distance) == [frozenset(hashes)]


def test_group_families_joins_roots_not_members():
    """Regression for the union-find step: f0-f1, f1-f3 and f2-f3 are near-duplicates. Linking a
    member instead of its root (parent[member] = root) ends with f0 split from f1."""
    a = 0
    b = a ^ 0b111
    d = b ^ (0b111 << 8)
    c = d ^ (0b111 << 16)
    groups = group_families({"f0": [a], "f1": [b], "f2": [c], "f3": [d]}, max_distance=4)
    assert groups == [frozenset({"f0", "f1", "f2", "f3"})]


# --- split.split_groups ---------------------------------------------------------------------

strata_maps = st.dictionaries(st.text("abcdefgh0123456789", min_size=1, max_size=6),
                              st.sampled_from(("rbb", "wsb", "mixed")), max_size=60)


@st.composite
def sized_strata(draw):
    """Strata of up to 300 groups each, so the 15 percent rounding is exercised at real sizes."""
    strata = {}
    for name in ("rbb", "wsb", "mixed"):
        for i in range(draw(st.integers(0, 300))):
            strata[f"{name}{i}"] = name
    return strata


@given(strata_maps, st.integers(0, 2**32))
def test_split_assigns_every_group_exactly_once(strata, seed):
    split = split_groups(strata, seed=seed)
    assert set(split) == set(strata)
    assert set(split.values()) <= {"train", "val", "test"}


@given(sized_strata(), st.integers(0, 2**32))
def test_split_counts_per_stratum_are_the_nearest_to_15_percent(strata, seed):
    split = split_groups(strata, seed=seed)
    for name in set(strata.values()):
        n = sum(s == name for s in strata.values())
        counts = Counter(split[g] for g, s in strata.items() if s == name)
        assert abs(counts["val"] - Fraction(15, 100) * n) <= Fraction(1, 2)
        assert abs(counts["test"] - Fraction(15, 100) * n) <= Fraction(1, 2)
        assert counts["train"] == n - counts["val"] - counts["test"]


@given(strata_maps, st.integers(0, 2**32), st.randoms(use_true_random=False))
def test_split_ignores_dictionary_order(strata, seed, rnd):
    items = list(strata.items())
    rnd.shuffle(items)
    assert split_groups(dict(items), seed=seed) == split_groups(strata, seed=seed)


def test_split_depends_on_the_seed_and_shuffles():
    """Guards against a seed that is ignored or a missing shuffle (sorted order would put the
    first names in val and test)."""
    strata = {f"g{i:03d}": "rbb" for i in range(100)}
    first, second = split_groups(strata, seed=1), split_groups(strata, seed=2)
    assert first != second
    assert {first[f"g{i:03d}"] for i in range(15)} != {"val"}


@given(clustered_hashes(), st.integers(0, 8), st.integers(0, 2**32))
def test_family_split_never_puts_near_duplicates_in_different_splits(hashes, max_distance, seed):
    """The whole leakage guarantee: group near-duplicate families, split the groups, and no two
    families within max_distance of each other end up in different splits."""
    groups = sorted(sorted(g) for g in group_families(hashes, max_distance))
    group_name = {f: f"group{i}" for i, g in enumerate(groups) for f in g}
    split = split_groups({f"group{i}": ("rbb", "wsb", "mixed")[i % 3] for i in range(len(groups))},
                         seed=seed)
    for a in hashes:
        for b in hashes:
            if _close(hashes, a, b, max_distance):
                assert split[group_name[a]] == split[group_name[b]]


# --- metrics --------------------------------------------------------------------------------


def _within_exact(pred: int, ref: int) -> bool:
    """The written rule, in exact arithmetic: +-1 below 10, else within 10 percent."""
    if ref < 10:
        return abs(pred - ref) <= 1
    return abs(pred - ref) <= Fraction(ref, 10)


def test_float_tolerance_matches_exact_rule_exhaustively():
    """Every reference up to 2000, every prediction from 3 past one end of the band to 3 past the
    other: 0.10 * ref is a float and must never flip a decision at the boundary."""
    for ref in range(2000):
        for pred in range(max(0, ref - ref // 10 - 3), ref + ref // 10 + 4):
            assert count_within_tolerance(pred, ref) == _within_exact(pred, ref), (pred, ref)


@given(st.integers(0, 10**12), st.integers(-3, 3))
def test_float_tolerance_matches_exact_rule_for_large_counts(ref, offset):
    for pred in (ref - ref // 10 + offset, ref + ref // 10 + offset):
        if pred >= 0:
            assert count_within_tolerance(pred, ref) == _within_exact(pred, ref)


@given(st.integers(0, 10**6), st.integers(0, 10**5), st.integers(0, 10**5), st.booleans(), st.booleans())
def test_closer_prediction_never_fails_where_farther_passes(ref, d1, d2, up1, up2):
    d1, d2 = sorted((d1 % (ref // 5 + 4), d2 % (ref // 5 + 4)))
    p1, p2 = ref + d1 if up1 else ref - d1, ref + d2 if up2 else ref - d2
    if p1 >= 0 and p2 >= 0 and count_within_tolerance(p2, ref):
        assert count_within_tolerance(p1, ref)


@st.composite
def paired_counts(draw):
    """(prediction, reference) per image, with predictions near the reference so images pass
    and fail in mixed proportions."""
    pairs = []
    for _ in range(draw(st.integers(1, 30))):
        ref = {s: draw(st.integers(0, 200)) for s in SPECIES}
        pred = {s: max(0, ref[s] + draw(st.integers(-(ref[s] // 5) - 2, ref[s] // 5 + 2))) for s in SPECIES}
        pairs.append((pred, ref))
    return pairs


@given(paired_counts())
def test_count_accuracy_is_the_fraction_of_passing_images(pairs):
    preds, refs = [p for p, _ in pairs], [r for _, r in pairs]
    acc = count_accuracy(preds, refs)
    passed = sum(all(count_within_tolerance(p[s], r[s]) for s in SPECIES) for p, r in pairs)
    assert acc == passed / len(pairs)
    assert count_accuracy(refs, refs) == 1.0


@given(paired_counts(), st.randoms(use_true_random=False))
def test_count_accuracy_ignores_image_order(pairs, rnd):
    shuffled = pairs[:]
    rnd.shuffle(shuffled)
    assert count_accuracy([p for p, _ in pairs], [r for _, r in pairs]) == \
        count_accuracy([p for p, _ in shuffled], [r for _, r in shuffled])


@given(paired_counts())
def test_count_errors_are_consistent(pairs):
    preds, refs = [p for p, _ in pairs], [r for _, r in pairs]
    errors = count_errors(preds, refs)
    perfect = count_errors(refs, refs)
    for s in SPECIES:
        e = errors[s]
        diffs = [p[s] - r[s] for p, r in pairs]
        assert e["bias"] == pytest.approx(sum(diffs) / len(diffs))
        assert e["mae"] == pytest.approx(sum(map(abs, diffs)) / len(diffs))
        assert e["exact"] == sum(d == 0 for d in diffs) / len(diffs)
        present = [(p[s], r[s]) for p, r in pairs if r[s] > 0]
        if present:
            assert e["presence_recall"] == sum(p > 0 for p, _ in present) / len(present)
        else:
            assert e["presence_recall"] is None
        bins = [b for b in e["mae_by_density"].values() if b["images"]]
        assert sum(b["images"] for b in bins) == len(present)
        assert all(b["mae"] >= 0 for b in bins)
        if present:
            weighted = sum(b["mae"] * b["images"] for b in bins) / len(present)
            assert weighted == pytest.approx(sum(abs(p - r) for p, r in present) / len(present))
        assert perfect[s]["mae"] == 0 and perfect[s]["bias"] == 0 and perfect[s]["exact"] == 1.0


# --- infer.postprocess ----------------------------------------------------------------------

N_QUERIES = 40
# Logits on a grid of quarters in [-8, 8]: equal logits give exactly equal scores, so ties occur,
# and distinct logits stay distinct after the sigmoid (float64 starts merging them near 24).
logit_grids = st.lists(st.lists(st.integers(-32, 32).map(lambda k: k / 4), min_size=4, max_size=4),
                       min_size=N_QUERIES, max_size=N_QUERIES)
thresholds = st.sampled_from([0.0, 0.1, 0.25, 0.5, 0.5621765008857981, 0.75, 0.9, 1.0])


def _run(logits, threshold):
    """Each query's box encodes its index in cx, so the output order can be read back."""
    lg = np.array(logits, dtype=np.float32)[None]
    boxes = np.zeros((1, N_QUERIES, 4), dtype=np.float32)
    boxes[0, :, 0] = (np.arange(N_QUERIES) + 0.5) / N_QUERIES
    boxes[0, :, 2:] = 0.01
    dets = postprocess(lg, boxes, N_QUERIES, 100, threshold=threshold)
    return [(round((d.x0 + d.x1) / 2 - 0.5), d) for d in dets]


@given(logit_grids, thresholds)
def test_postprocess_orders_by_score_then_query(logits, threshold):
    out = _run(logits, threshold)
    keys = [(-d.score, q) for q, d in out]
    assert keys == sorted(keys)


@given(logit_grids, thresholds)
# A logit of exactly 0 scores exactly 0.5, so this pins the inclusive (>=) boundary every run.
@example([[0.0, -8.0, -8.0, -8.0]] + [[-8.0] * 4] * (N_QUERIES - 1), 0.5)
def test_postprocess_keeps_exactly_the_queries_at_or_above_threshold(logits, threshold):
    out = _run(logits, threshold)
    probs = 1.0 / (1.0 + np.exp(-np.array(logits, dtype=np.float32).astype(np.float64)))
    assert sorted(q for q, _ in out) == [q for q in range(N_QUERIES) if probs[q].max() >= threshold]
    for q, d in out:
        assert d.class_id == int(probs[q].argmax())
        assert d.score >= threshold


distinct_thresholds = st.lists(thresholds, min_size=2, max_size=2, unique=True).map(sorted)


@given(logit_grids, distinct_thresholds)
def test_raising_the_threshold_keeps_a_prefix(logits, pair):
    lo, hi = pair
    low, high = _run(logits, lo), _run(logits, hi)
    assert [q for q, _ in high] == [q for q, _ in low][:len(high)]


@given(logit_grids, distinct_thresholds)
def test_species_counts_never_rise_with_the_threshold(logits, pair):
    lo, hi = pair
    low = Counter(SPECIES_OF_CLASS[d.class_id] for _, d in _run(logits, lo))
    high = Counter(SPECIES_OF_CLASS[d.class_id] for _, d in _run(logits, hi))
    assert all(high[s] <= low[s] for s in SPECIES)


@settings(max_examples=50)
@given(st.lists(st.tuples(st.floats(0, 1), st.floats(0, 1), st.floats(0, 1), st.floats(0, 1)),
                min_size=1, max_size=10),
       st.integers(1, 5000), st.integers(1, 5000))
def test_postprocess_boxes_are_centre_size_scaled_to_the_image(raw_boxes, width, height):
    n = len(raw_boxes)
    logits = np.full((1, n, 4), 5.0, dtype=np.float32)
    boxes = np.array(raw_boxes, dtype=np.float32)[None]
    dets = postprocess(logits, boxes, width, height)
    assert len(dets) == n
    for d, (cx, cy, w, h) in zip(dets, boxes[0].astype(np.float64), strict=True):
        assert d.x0 <= d.x1 and d.y0 <= d.y1
        assert (d.x0 + d.x1) / 2 == pytest.approx(cx * width, abs=1e-6)
        assert (d.y0 + d.y1) / 2 == pytest.approx(cy * height, abs=1e-6)
        assert d.x1 - d.x0 == pytest.approx(w * width, abs=1e-6)
        assert d.y1 - d.y0 == pytest.approx(h * height, abs=1e-6)
