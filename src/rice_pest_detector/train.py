"""Fine-tune RT-DETR on the split manifest; resumable checkpoints; validation-only selection."""

import hashlib
import json
import math
import random
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np
import torch
from PIL import Image
from torch.utils.data import DataLoader, Dataset
from transformers import AutoModelForObjectDetection, RTDetrConfig, RTDetrForObjectDetection

from rice_pest_detector import CLASS_NAMES
from rice_pest_detector.infer import postprocess, preprocess
from rice_pest_detector.metrics import confusion, count_accuracy, count_errors, map50, species_counts

EVALUATOR_VERSION = 2  # bump whenever evaluate() changes what it measures


@dataclass
class TrainConfig:
    base_model: str
    revision: str
    epochs: int = 60
    batch_size: int = 8
    lr: float = 1e-4
    backbone_lr: float = 1e-5
    weight_decay: float = 1e-4
    grad_clip: float = 0.1
    seed: int = 20261013
    num_queries: int = 300
    fp16: bool = True
    num_workers: int = 2
    input_size: int = 640  # model input side; 640 is the app contract


class ManifestDataset(Dataset):
    def __init__(self, manifest: dict, image_root: Path, split: str, size: int = 640):
        self.records = [r for r in manifest["images"] if r["split"] == split]
        self.root = Path(image_root)
        self.size = size

    def __len__(self) -> int:
        return len(self.records)

    def __getitem__(self, i: int):
        rec = self.records[i]
        with Image.open(self.root / rec["relative_path"]) as img:
            pixels = torch.from_numpy(preprocess(img, self.size)[0])
        boxes = rec["boxes"]
        target = {"class_labels": torch.tensor([b[0] for b in boxes], dtype=torch.long),
                  "boxes": torch.tensor([b[1:] for b in boxes], dtype=torch.float32).reshape(-1, 4)}
        return pixels, target


def collate(batch):
    return torch.stack([b[0] for b in batch]), [b[1] for b in batch]


def _tiny_config() -> RTDetrConfig:  # replaced in tests
    raise RuntimeError("tiny config only available in tests")


def build_model(cfg: TrainConfig):
    """RT-DETR or D-FINE: the checkpoint's own config picks the class (same sigmoid logits / cxcywh boxes)."""
    if cfg.base_model == "__tiny__":
        model = RTDetrForObjectDetection(_tiny_config())
    else:
        id2label = dict(enumerate(CLASS_NAMES))
        model = AutoModelForObjectDetection.from_pretrained(
            cfg.base_model, revision=cfg.revision, num_labels=len(CLASS_NAMES), id2label=id2label,
            label2id={v: k for k, v in id2label.items()}, num_queries=cfg.num_queries,
            ignore_mismatched_sizes=True,
        )
    model.loss_function = fp32_loss(model.loss_function)
    return model


def _to_fp32(value):
    if torch.is_tensor(value):
        return value.float() if value.is_floating_point() else value
    if isinstance(value, dict):
        return {k: _to_fp32(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return type(value)(_to_fp32(v) for v in value)
    return value


def fp32_loss(loss_fn):
    """Run RT-DETR's matcher and losses in float32 even under fp16 autocast.

    The Hungarian matcher takes log(p + 1e-8) of sigmoid scores; in float16 the epsilon
    underflows and saturated logits give inf costs, which scipy rejects with ValueError
    before the training loop's finite-loss check can run. The final, auxiliary and encoder
    outputs all pass through this one call.
    """
    def wrapped(*args, **kwargs):
        device_type = "cuda" if torch.cuda.is_available() else "cpu"
        with torch.autocast(device_type=device_type, enabled=False):
            return loss_fn(*_to_fp32(args), **_to_fp32(kwargs))
    wrapped.__wrapped__ = loss_fn
    return wrapped


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha256_json(obj) -> str:
    return _sha256_bytes(json.dumps(obj, sort_keys=True).encode("utf-8"))


def experiment_id(cfg: TrainConfig, manifest: dict, val_annotations: bytes) -> dict:
    """What makes two runs the same experiment; num_workers only changes speed."""
    settings = {k: v for k, v in asdict(cfg).items() if k != "num_workers"}
    if settings.get("input_size") == 640:  # runs from before the field existed keep their identity
        del settings["input_size"]
    return {"config": settings, "manifest_sha256": _sha256_json(manifest),
            "annotations_val_sha256": _sha256_bytes(val_annotations)}


def check_experiment(saved: dict | None, current: dict) -> None:
    if saved is None:
        print("WARNING: last.pt predates experiment fingerprints; resuming without an identity check")
        return
    if saved != current:
        changed = sorted(k for k in saved["config"].keys() | current["config"].keys()
                         if saved["config"].get(k) != current["config"].get(k))
        changed += [k for k in ("manifest_sha256", "annotations_val_sha256") if saved.get(k) != current.get(k)]
        raise RuntimeError(f"run directory holds a different experiment (changed: {', '.join(changed)}); "
                           "use a new RUN_DIR instead of resuming")


def _rng_state() -> dict:
    name, keys, pos, has_gauss, cached = np.random.get_state()
    return {"python": random.getstate(), "numpy": [name, keys.tolist(), pos, has_gauss, cached],
            "torch": torch.get_rng_state(),
            "cuda": torch.cuda.get_rng_state_all() if torch.cuda.is_available() else []}


def _set_rng_state(state: dict) -> None:
    version, internal, gauss = state["python"]
    random.setstate((version, tuple(internal), gauss))
    name, keys, pos, has_gauss, cached = state["numpy"]
    np.random.set_state((name, np.array(keys, dtype=np.uint32), pos, has_gauss, cached))
    torch.set_rng_state(state["torch"])
    if state["cuda"] and torch.cuda.is_available():
        torch.cuda.set_rng_state_all(state["cuda"])


def _atomic_save(obj, path: Path) -> None:
    path = Path(path)
    tmp = path.with_name(path.name + ".tmp")
    torch.save(obj, tmp)
    tmp.replace(path)


def _atomic_write_text(path: Path, text: str) -> None:
    path = Path(path)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(text)
    tmp.replace(path)


def save_checkpoint(path: Path, model, optimizer, scheduler, epoch: int, best_metric: float,
                    scaler=None, experiment: dict | None = None) -> None:
    _atomic_save({"model": model.state_dict(), "optimizer": optimizer.state_dict(),
                  "scheduler": scheduler.state_dict(), "epoch": epoch, "best_metric": best_metric,
                  "scaler": scaler.state_dict() if scaler is not None else {},
                  "experiment": experiment, "rng": _rng_state()}, path)


def load_checkpoint(path: Path, model, optimizer, scheduler, scaler=None,
                    experiment: dict | None = None) -> tuple[int, float]:
    state = torch.load(path, map_location="cpu", weights_only=True)
    if experiment is not None:
        check_experiment(state.get("experiment"), experiment)
    model.load_state_dict(state["model"])
    optimizer.load_state_dict(state["optimizer"])
    scheduler.load_state_dict(state["scheduler"])
    if scaler is not None and state.get("scaler"):
        scaler.load_state_dict(state["scaler"])
    if state.get("rng"):
        _set_rng_state(state["rng"])
    return state["epoch"] + 1, state["best_metric"]


def load_best(path: Path) -> tuple[dict, dict]:
    """Return (state_dict, metadata) from best.pt; older runs saved a bare state_dict."""
    state = torch.load(path, map_location="cpu", weights_only=True)
    if "model" in state and "map50_species" in state:
        return state["model"], {k: v for k, v in state.items() if k != "model"}
    return state, {}


def record_best(run_dir: Path, model, score: float, epoch: int, best: float,
                experiment: dict | None = None) -> float:
    """Save weights, score and epoch together in one atomic best.pt if `score` beats `best`.

    best.json is a human-readable copy written afterwards; resume trusts best.pt, so an
    interruption between the two writes cannot pair new weights with an old score.
    """
    if not math.isfinite(score) or score <= best:
        return best
    run_dir = Path(run_dir)
    _atomic_save({"model": model.state_dict(), "map50_species": score, "epoch": epoch,
                  "experiment": experiment}, run_dir / "best.pt")
    _atomic_write_text(run_dir / "best.json", json.dumps({"map50_species": score, "epoch": epoch}))
    return score


MAX_NONFINITE_STEPS = 50


def read_history(path: Path) -> list[dict]:
    """Parse history.jsonl, dropping a final line cut short by a disconnect; any other bad line raises."""
    lines = [ln for ln in Path(path).read_text().splitlines() if ln.strip()]
    rows = []
    for i, ln in enumerate(lines):
        try:
            rows.append(json.loads(ln))
        except json.JSONDecodeError:
            if i != len(lines) - 1:
                raise
            print(f"WARNING: dropping truncated final history line: {ln[:60]!r}")
    return rows


def trim_history(path: Path, start: int) -> None:
    """Drop history rows with epoch >= start so a resumed run does not duplicate epochs."""
    path = Path(path)
    if not path.exists():
        return
    rows = [r for r in read_history(path) if r["epoch"] < start]
    _atomic_write_text(path, "".join(json.dumps(r) + "\n" for r in rows))


def resume_best(run_dir: Path, ckpt_best: float) -> float:
    """Best metric on resume: last.pt may lag best.pt by one epoch after an interruption."""
    run_dir = Path(run_dir)
    if (run_dir / "best.pt").exists():
        _, meta = load_best(run_dir / "best.pt")
        if meta:
            return max(ckpt_best, meta["map50_species"])
    sidecar = run_dir / "best.json"  # runs from before best.pt carried its own score
    if sidecar.exists():
        return max(ckpt_best, json.loads(sidecar.read_text())["map50_species"])
    return ckpt_best


def _quantiles(values: list[float]) -> dict[str, float]:
    if not values:
        return {}
    q = np.quantile(values, [0.5, 0.9, 1.0])
    return {"p50": float(q[0]), "p90": float(q[1]), "max": float(q[2])}


@torch.no_grad()
def evaluate(model, dataset: ManifestDataset, coco_gt: dict, threshold: float = 0.5) -> dict:
    model.eval()
    device = next(model.parameters()).device
    dets, preds, refs, table, top_scores, kept_total = [], [], [], {}, [], 0
    for image_id, rec in enumerate(dataset.records, start=1):
        assert coco_gt["images"][image_id - 1]["file_name"] == rec["file"], (
            f"COCO image {image_id} is {coco_gt['images'][image_id - 1]['file_name']!r} "
            f"but manifest record is {rec['file']!r}")
        pixels, _ = dataset[image_id - 1]
        out = model(pixel_values=pixels[None].to(device))
        found = postprocess(out.logits.float().cpu().numpy(), out.pred_boxes.float().cpu().numpy(),
                            rec["width"], rec["height"], threshold=0.0)
        dets += [{"image_id": image_id, "category_id": d.class_id + 1, "score": d.score,
                  "bbox": [d.x0, d.y0, d.x1 - d.x0, d.y1 - d.y0]} for d in found]
        top_scores.append(found[0].score if found else 0.0)
        kept = [d for d in found if d.score >= threshold]
        kept_total += len(kept)
        preds.append(species_counts([d.class_id for d in kept]))
        refs.append(species_counts([b[0] for b in rec["boxes"]]))
        w, h = rec["width"], rec["height"]
        gt = [(c, [(cx - bw / 2) * w, (cy - bh / 2) * h, (cx + bw / 2) * w, (cy + bh / 2) * h])
              for c, cx, cy, bw, bh in rec["boxes"]]
        for key, n in confusion(gt, [(d.class_id, [d.x0, d.y0, d.x1, d.y1]) for d in kept]).items():
            table[key] = table.get(key, 0) + n
    zero = [species_counts([]) for _ in refs]
    return {"map50_species": map50(coco_gt, dets, group_species=True)["all"],
            "map50_by_class": map50(coco_gt, dets, group_species=False),
            "threshold": threshold,
            "count_accuracy": count_accuracy(preds, refs),
            "count_accuracy_no_detection_baseline": count_accuracy(zero, refs),
            "count_errors": count_errors(preds, refs),
            "detections_kept": kept_total,
            "top_score_per_image": _quantiles(top_scores),
            "confusion": {f"{g}->{p}": n for (g, p), n in sorted(table.items())}}


def evaluation_id(best_path: Path, manifest: dict, coco_path: Path, threshold: float) -> dict:
    """Everything a cached test result depends on, not just the weights."""
    return {"best_pt_sha256": _sha256_bytes(Path(best_path).read_bytes()),
            "manifest_sha256": _sha256_json(manifest),
            "annotations_sha256": _sha256_bytes(Path(coco_path).read_bytes()),
            "threshold": threshold, "evaluator_version": EVALUATOR_VERSION}


def check_cached_test(prior: dict, current: dict) -> None:
    """Refuse a cached test result that no longer describes the current evaluation."""
    saved = prior.get("evaluation")
    if saved is None:  # legacy record: bound to the weights only
        if prior.get("best_pt_sha256") != current["best_pt_sha256"]:
            raise RuntimeError("best.pt changed after the test split was evaluated: protocol violation, "
                               "stop and ask the owner")
        return
    changed = [k for k in current if saved.get(k) != current[k]]
    if changed:
        raise RuntimeError(f"test split already evaluated under a different setup (changed: "
                           f"{', '.join(changed)}): protocol violation, stop and ask the owner")


def fit(cfg: TrainConfig, manifest: dict, image_root: Path, run_dir: Path) -> Path:
    random.seed(cfg.seed)
    np.random.seed(cfg.seed)
    torch.manual_seed(cfg.seed)
    run_dir = Path(run_dir)
    run_dir.mkdir(parents=True, exist_ok=True)
    device = "cuda" if torch.cuda.is_available() else "cpu"
    amp = cfg.fp16 and device == "cuda"
    val_bytes = (run_dir / "annotations_val.json").read_bytes()
    experiment = experiment_id(cfg, manifest, val_bytes)
    model = build_model(cfg).to(device)
    backbone = [p for n, p in model.named_parameters() if "backbone" in n]
    rest = [p for n, p in model.named_parameters() if "backbone" not in n]
    opt = torch.optim.AdamW([{"params": rest, "lr": cfg.lr}, {"params": backbone, "lr": cfg.backbone_lr}],
                            weight_decay=cfg.weight_decay)
    sched = torch.optim.lr_scheduler.CosineAnnealingLR(opt, T_max=cfg.epochs)
    scaler = torch.amp.GradScaler(device, enabled=amp)
    start, best = 0, -1.0
    if (run_dir / "last.pt").exists():
        start, best = load_checkpoint(run_dir / "last.pt", model, opt, sched, scaler=scaler,
                                      experiment=experiment)
        best = resume_best(run_dir, best)
        trim_history(run_dir / "history.jsonl", start)
        print(f"resumed at epoch {start}, best val mAP50 {best:.4f}")
    train_set = ManifestDataset(manifest, image_root, "train", size=cfg.input_size)
    if len(train_set) == 0:
        raise ValueError("train split is empty")
    val_set = ManifestDataset(manifest, image_root, "val", size=cfg.input_size)
    val_coco = json.loads(val_bytes)
    _atomic_write_text(run_dir / "config.json", json.dumps({**asdict(cfg), "experiment": experiment}, indent=1))
    for epoch in range(start, cfg.epochs):
        train = DataLoader(train_set, batch_size=cfg.batch_size, shuffle=True, collate_fn=collate,
                           num_workers=cfg.num_workers, generator=torch.Generator().manual_seed(cfg.seed + epoch))
        model.train()
        total, steps, updates, bad_loss, bad_grad, bad = 0.0, 0, 0, 0, 0, 0
        step_no = -1
        for pixels, targets in train:
            step_no += 1
            targets = [{k: v.to(device) for k, v in t.items()} for t in targets]
            opt.zero_grad(set_to_none=True)
            with torch.autocast(device_type=device, enabled=amp):
                loss = model(pixel_values=pixels.to(device), labels=targets).loss
            if not torch.isfinite(loss.detach()):
                bad_loss += 1
                bad += 1
            else:
                total += loss.detach().item()
                steps += 1
                scaler.scale(loss).backward()
                scaler.unscale_(opt)
                norm = torch.nn.utils.clip_grad_norm_(model.parameters(), cfg.grad_clip)
                if torch.isfinite(norm):
                    scaler.step(opt)
                    updates += 1
                    bad = 0
                else:  # skip the update; under AMP the scaler also lowers its scale
                    bad_grad += 1
                    bad += 1
                scaler.update()
            if bad >= MAX_NONFINITE_STEPS:
                raise RuntimeError(
                    f"loss or gradient non-finite for {bad} consecutive steps (epoch {epoch}, step {step_no}); "
                    "training diverged, stopping")
        if updates == 0:
            raise RuntimeError(f"epoch {epoch}: no optimizer updates (all losses or gradients non-finite)")
        sched.step()
        metrics = evaluate(model, val_set, val_coco)
        row = {"epoch": epoch, "train_loss": total / steps, "updates": updates,
               "nonfinite_loss_steps": bad_loss, "skipped_updates": bad_grad,
               "grad_scale": scaler.get_scale() if amp else None, **metrics}
        print(json.dumps({k: v for k, v in row.items() if k != "confusion"}))
        with (run_dir / "history.jsonl").open("a") as fh:
            fh.write(json.dumps(row) + "\n")
        best = record_best(run_dir, model, metrics["map50_species"], epoch, best, experiment=experiment)
        save_checkpoint(run_dir / "last.pt", model, opt, sched, epoch, best, scaler=scaler,
                        experiment=experiment)
    return run_dir / "best.pt"
