"""Build the leakage-free split manifest and COCO annotations from the local dataset."""

import argparse
import hashlib
import json
from collections import defaultdict
from pathlib import Path

import numpy as np
from PIL import Image

from rice_pest_detector import CLASS_NAMES
from rice_pest_detector.dedup import dhash, group_families
from rice_pest_detector.families import family_key
from rice_pest_detector.labels import Box, load_label_file, validate_boxes
from rice_pest_detector.split import Variant, select_eval_variant, split_groups, stratum

_SPLITS = ("train", "valid", "test")

# Measured on the real dataset: see "Data preparation" in docs/evaluation-record.md.
DEDUP_MAX_DISTANCE = 1


def _representative(items: list[dict]) -> tuple[dict, str | None]:
    """The family's representative image, chosen by the evaluation-variant rule."""
    variants = [Variant(i["path"].name, i["origin"], i["grey"]) for i in items]
    pick, rule = select_eval_variant(variants)
    return next(i for i in items if i["path"].name == pick.name), rule


def _is_grey(img: Image.Image) -> bool:
    a = np.asarray(img.convert("RGB"), dtype=np.int16)
    return bool(np.abs(a[..., 0] - a[..., 1]).max() <= 2 and np.abs(a[..., 1] - a[..., 2]).max() <= 2)


def _scan(root: Path) -> tuple[dict[str, list[dict]], list[dict]]:
    families: dict[str, list[dict]] = defaultdict(list)
    for origin in _SPLITS:
        image_dir = root / "02_detection_dataset" / origin / "images"
        for path in sorted(image_dir.glob("*")):
            if path.suffix.lower() not in {".jpg", ".jpeg", ".png"}:
                continue
            families[family_key(path.name)].append({"path": path, "origin": origin})
    exclusions: list[dict] = []
    for fam in sorted(families):
        for item in families[fam]:
            label = item["path"].parent.parent / "labels" / (item["path"].stem + ".txt")
            try:
                item["boxes"] = load_label_file(label)
            except FileNotFoundError:
                exclusions.append({"family": fam, "reason": f"missing label for {item['path'].name}"})
                break
            except ValueError as exc:
                exclusions.append({"family": fam, "reason": f"{item['path'].name}: {exc}"})
                break
            errors = validate_boxes(item["boxes"])
            if errors:
                exclusions.append({"family": fam, "reason": f"{item['path'].name}: {errors[0]}"})
                break
    for e in exclusions:
        families.pop(e["family"], None)
    return families, exclusions


def _coco(records: list[dict]) -> dict:
    images, annotations = [], []
    for image_id, rec in enumerate(records, start=1):
        w, h = rec["width"], rec["height"]
        images.append({"id": image_id, "file_name": rec["file"], "width": w, "height": h})
        for c, cx, cy, bw, bh in rec["boxes"]:
            box = [(cx - bw / 2) * w, (cy - bh / 2) * h, bw * w, bh * h]
            annotations.append({"id": len(annotations) + 1, "image_id": image_id, "category_id": c + 1,
                                "bbox": box, "area": box[2] * box[3], "iscrowd": 0})
    categories = [{"id": i + 1, "name": n} for i, n in enumerate(CLASS_NAMES)]
    return {"images": images, "annotations": annotations, "categories": categories}


def prepare(dataset_root: Path, out_dir: Path, seed: int = 20261013, num_queries: int = 300) -> dict:
    root = Path(dataset_root)
    families, exclusions = _scan(root)
    for fam, items in families.items():
        for item in items:
            if len(item["boxes"]) > num_queries:
                raise ValueError(f"{item['path'].name}: {len(item['boxes'])} boxes exceeds "
                                 f"num_queries={num_queries}")
            with Image.open(item["path"]) as img:
                item["grey"], item["size"] = _is_grey(img), img.size
                item["hash"] = dhash(img)
    rep_hashes = {f: [_representative(items)[0]["hash"]] for f, items in families.items()}
    groups = group_families(rep_hashes, max_distance=DEDUP_MAX_DISTANCE)
    group_of = {f: f"grp{n:05d}" for n, g in enumerate(sorted(groups, key=sorted)) for f in g}
    group_boxes: dict[str, list[Box]] = defaultdict(list)
    for fam, items in families.items():
        group_boxes[group_of[fam]].extend(b for i in items for b in i["boxes"])
    split_of_group = split_groups({g: stratum(b) for g, b in group_boxes.items()}, seed=seed)

    records: list[dict] = []
    for fam in sorted(families):
        items, split = families[fam], split_of_group[group_of[fam]]
        chosen, rule = items, None
        if split != "train":
            pick, rule = _representative(items)
            chosen = [pick]
        for item in chosen:
            rel = item["path"].relative_to(root).as_posix()
            data = item["path"].read_bytes()
            records.append({
                "file": item["path"].name, "relative_path": rel, "archive_member": f"datasets/{rel}",
                "family": fam, "group": group_of[fam], "split": split, "origin_split": item["origin"],
                "selection_rule": rule, "sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data),
                "width": item["size"][0], "height": item["size"][1],
                "boxes": [[b.class_id, b.cx, b.cy, b.w, b.h] for b in item["boxes"]],
            })

    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    (out / "split_manifest.json").write_text(json.dumps({"seed": seed, "images": records}, indent=1),
                                             encoding="utf-8", newline="\n")
    (out / "exclusions.json").write_text(json.dumps(exclusions, indent=1), encoding="utf-8", newline="\n")
    for split in ("train", "val", "test"):
        coco = _coco([r for r in records if r["split"] == split])
        (out / f"annotations_{split}.json").write_text(json.dumps(coco), encoding="utf-8", newline="\n")
    counts = {s: sum(r["split"] == s for r in records) for s in ("train", "val", "test")}
    return {"images": counts, "families": len(families), "groups": len(groups),
            "excluded_families": len(exclusions)}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset-root", type=Path, required=True)
    parser.add_argument("--out", type=Path, default=Path("data"))
    args = parser.parse_args()
    print(json.dumps(prepare(args.dataset_root, args.out), indent=1))


if __name__ == "__main__":
    main()
