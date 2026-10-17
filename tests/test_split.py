from collections import Counter

from rice_pest_detector.labels import Box
from rice_pest_detector.split import Variant, select_eval_variant, split_groups, stratum


def test_stratum_classifies_species_mix():
    assert stratum([Box(0, .5, .5, .1, .1), Box(1, .2, .2, .1, .1)]) == "rbb"
    assert stratum([Box(3, .5, .5, .1, .1)]) == "wsb"
    assert stratum([Box(1, .5, .5, .1, .1), Box(2, .2, .2, .1, .1)]) == "mixed"


def test_split_groups_is_deterministic_and_proportional_per_stratum():
    strata = {f"g{i}": ("rbb" if i < 600 else "wsb" if i < 900 else "mixed") for i in range(1000)}
    first = split_groups(strata, seed=7)
    assert first == split_groups(strata, seed=7)
    assert set(first) == set(strata)
    for name, size in (("rbb", 600), ("wsb", 300), ("mixed", 100)):
        counts = Counter(first[g] for g, s in strata.items() if s == name)
        assert abs(counts["val"] - 0.15 * size) <= 1
        assert abs(counts["test"] - 0.15 * size) <= 1


def test_select_eval_variant_prefers_published_original_then_colour():
    published = [Variant("b.jpg", "train", False), Variant("a.jpg", "test", False)]
    assert select_eval_variant(published) == (published[1], "published-original")
    colour = [Variant("a.jpg", "train", True), Variant("b.jpg", "train", False)]
    assert select_eval_variant(colour) == (colour[1], "first-colour")
    grey = [Variant("b.jpg", "train", True), Variant("a.jpg", "train", True)]
    assert select_eval_variant(grey) == (grey[1], "first-any")
