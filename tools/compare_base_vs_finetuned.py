"""Compare the base checkpoint (new, untrained 4-class head) with a fine-tuned best.pt on VALIDATION.

The base model is COCO-pretrained, and COCO has no rice-pest classes, so "base" here means the
pinned backbone and encoder/decoder with the freshly initialised pest head, exactly as training
starts at epoch 0. Head initialisation is random, so the base model is scored under several seeds.
Both models go through train.evaluate(), the same evaluator the training run used. The test split
is never read.

Run: python -m tools.compare_base_vs_finetuned --best runs/run-r18/best.pt
         --image-root <riceprotek-insects-v28>/datasets --out runs/run-r18/base_vs_finetuned_val.json
"""

import argparse
import json
from pathlib import Path

import torch

from rice_pest_detector.train import (
    EVALUATOR_VERSION,
    ManifestDataset,
    TrainConfig,
    build_model,
    evaluate,
    load_best,
)

BASE = "PekingU/rtdetr_r18vd"
REVISION = "ac77a11ff0170a41b771c03264987f8ce2b0d753"
THRESHOLDS = (0.5, 0.04)  # specified threshold; demo threshold chosen on validation
SEEDS = (20261013, 1, 2)  # 20261013 is the training seed


def _summary(metrics: dict) -> dict:
    keep = ("map50_species", "map50_by_class", "threshold", "count_accuracy",
            "count_accuracy_no_detection_baseline", "count_errors", "detections_kept",
            "top_score_per_image")
    return {k: metrics[k] for k in keep}


def _score(model, val_set, coco) -> dict:
    return {str(t): _summary(evaluate(model, val_set, coco, threshold=t)) for t in THRESHOLDS}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--best", type=Path, required=True)
    ap.add_argument("--image-root", type=Path, required=True)
    ap.add_argument("--manifest", type=Path, default=Path("data/split_manifest.json"))
    ap.add_argument("--annotations", type=Path, default=Path("data/annotations_val.json"))
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args(argv)

    manifest = json.loads(args.manifest.read_text())
    coco = json.loads(args.annotations.read_text())
    val_set = ManifestDataset(manifest, args.image_root, "val")
    cfg = TrainConfig(base_model=BASE, revision=REVISION)
    torch.set_grad_enabled(False)

    report = {"split": "val", "images": len(val_set), "base_model": BASE, "revision": REVISION,
              "evaluator_version": EVALUATOR_VERSION, "base_untrained_head": {}}
    for seed in SEEDS:
        torch.manual_seed(seed)
        report["base_untrained_head"][str(seed)] = _score(build_model(cfg).eval(), val_set, coco)
        print(f"base seed {seed} done", flush=True)

    model = build_model(cfg)
    state, meta = load_best(args.best)
    model.load_state_dict(state)
    report["fine_tuned"] = {"checkpoint": str(args.best), "metadata": {k: meta[k] for k in ("epoch", "map50_species") if k in meta},
                            "scores": _score(model.eval(), val_set, coco)}
    print("fine-tuned done", flush=True)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=1) + "\n", encoding="utf-8", newline="\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
