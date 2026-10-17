"""Family-group split (70/15/15, stratified) and evaluation-variant selection."""

import random
from dataclasses import dataclass

from rice_pest_detector import SPECIES_OF_CLASS
from rice_pest_detector.labels import Box


def stratum(boxes: list[Box]) -> str:
    species = {SPECIES_OF_CLASS[b.class_id] for b in boxes}
    if species == {"RBB"}:
        return "rbb"
    if species == {"WSB"}:
        return "wsb"
    return "mixed"


def split_groups(
    group_strata: dict[str, str],
    seed: int = 20261013,
    ratios: tuple[float, float, float] = (0.70, 0.15, 0.15),
) -> dict[str, str]:
    rng = random.Random(seed)
    assignment: dict[str, str] = {}
    for name in sorted(set(group_strata.values())):
        groups = sorted(g for g, s in group_strata.items() if s == name)
        rng.shuffle(groups)
        n_val = round(ratios[1] * len(groups))
        n_test = round(ratios[2] * len(groups))
        for i, g in enumerate(groups):
            assignment[g] = "val" if i < n_val else "test" if i < n_val + n_test else "train"
    return assignment


@dataclass(frozen=True)
class Variant:
    name: str
    origin_split: str
    grayscale: bool


def select_eval_variant(variants: list[Variant]) -> tuple[Variant, str]:
    ordered = sorted(variants, key=lambda v: v.name)
    for v in ordered:
        if v.origin_split in {"valid", "test"}:
            return v, "published-original"
    for v in ordered:
        if not v.grayscale:
            return v, "first-colour"
    return ordered[0], "first-any"
