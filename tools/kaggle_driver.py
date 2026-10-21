"""Stage driver for the Kaggle editions, run inside the notebook's own Python environment.

The Kaggle notebook never imports torch, transformers, NumPy or Pillow in its kernel. It builds an isolated
environment from the committed hash lock and runs each stage as a child process:

    <env python> -u kaggle_driver.py --stage <name> --work /tmp/rpd --run-dir /kaggle/working/run-<variant>

The module itself imports only the standard library at the top; each stage imports what it needs, so the
helpers can be tested without torch. The package (`rice_pest_detector`) and `rpd_tools/export_onnx.py` are
the repository's own files, written by the notebook into the work folder.
"""

import argparse
import csv
import datetime
import hashlib
import json
import os
import platform
import shutil
import sys
import time
from pathlib import Path

RESUME_FILES = ("last.pt", "best.pt", "best.json", "history.jsonl", "config.json")
IMAGE_SUFFIXES = (".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff", ".webp", ".gif")
ARCHIVE_SUFFIXES = (".zip", ".tar", ".gz", ".tgz", ".7z")
OUTPUT_BUDGET_BYTES = 5 * 1000**3
SPLIT_SIZES = {"train": 4948, "val": 253, "test": 252}
MAX_QUERIES = 300
RELOAD_PHOTOS = 10
INFERENCE_PHOTOS = (10, 22)  # validation records 10-21, after the reload photos
CROWDED = 30
UV_VERSION = "0.12.15"
LOCK_NAME = "requirements-kaggle.lock.txt"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_json(path: Path, obj) -> None:
    path = Path(path)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(obj, indent=1) + "\n", encoding="utf-8")
    tmp.replace(path)


def read_json(path: Path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


class Context:
    """Paths and settings of one run; `edition.json` is written by the notebook's `paths` cell."""

    def __init__(self, work: Path, run_dir: Path, input_root: Path = Path("/kaggle/input")):
        self.work, self.run_dir, self.input_root = Path(work), Path(run_dir), Path(input_root)
        self.edition = read_json(self.work / "edition.json")
        self.images = self.work / "images"
        self.data = self.work / "data"

    def manifest(self) -> dict:
        return read_json(self.data / "split_manifest.json")

    def records(self, split: str) -> list[dict]:
        return [r for r in self.manifest()["images"] if r["split"] == split]


# ---------------------------------------------------------------- fetch


def pins_ok(path: Path, size: int, md5: str, sha256: str) -> bool:
    path = Path(path)
    if not path.is_file() or path.stat().st_size != size:
        return False
    h_md5, h_sha = hashlib.md5(), hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h_md5.update(chunk)
            h_sha.update(chunk)
    return h_md5.hexdigest() == md5 and h_sha.hexdigest() == sha256


def find_attached_archive(root: Path, size: int, md5: str, sha256: str) -> Path | None:
    """A reader's own attached `datasets.zip` anywhere under `root`, used only if it passes all three pins."""
    root = Path(root)
    if not root.is_dir():
        return None
    for candidate in sorted(root.rglob("datasets.zip")):
        if pins_ok(candidate, size, md5, sha256):
            return candidate
        print(f"ignoring {candidate}: it does not match the Zenodo size, MD5 and SHA-256")
    return None


def stage_fetch(ctx: Context) -> None:
    from rice_pest_detector import fetch

    pins = (fetch.ZENODO_BYTES, fetch.ZENODO_MD5, fetch.ZENODO_SHA256)
    archive = find_attached_archive(ctx.input_root, *pins)
    if archive is not None:
        print("using the attached archive (size, MD5 and SHA-256 match the Zenodo record)")
    else:
        dest = ctx.work / "datasets.zip"
        if pins_ok(dest, *pins):
            archive = dest
            print("verified archive already in scratch, skipping download")
        else:
            print(f"downloading the dataset archive from Zenodo ({fetch.ZENODO_BYTES / 1e9:.2f} GB) to scratch")
            try:
                archive = fetch.download(fetch.ZENODO_URL, dest, *pins)
            except ValueError as exc:
                raise SystemExit(f"Download check failed (size, MD5 or SHA-256): {exc}. Nothing was trained; "
                                 "run the notebook again later.") from None
            except OSError as exc:
                raise SystemExit(f"Download from Zenodo failed: {exc}. Check that Internet is on in Settings "
                                 "and that zenodo.org is reachable, then run again.") from None
    n = fetch.extract_members(archive, ctx.manifest(), ctx.images)
    print(n, "images extracted to scratch and verified against the committed split manifest (SHA-256)")
    shutil.copy(ctx.data / "annotations_val.json", ctx.run_dir / "annotations_val.json")


# ---------------------------------------------------------------- validate


def validation_problems(manifest: dict, image_sizes: dict[str, tuple[int, int]] | None = None) -> tuple[dict, list]:
    """Checks made before training. Returns (table, problems); `image_sizes` maps file -> (width, height)."""
    records = manifest["images"]
    problems = []
    sizes = {s: sum(r["split"] == s for r in records) for s in SPLIT_SIZES}
    if sizes != SPLIT_SIZES:
        problems.append(f"split sizes {sizes} != {SPLIT_SIZES}")
    names = [r["file"] for r in records]
    duplicates = sorted({n for n in names if names.count(n) > 1}) if len(set(names)) != len(names) else []
    if duplicates:
        problems.append(f"duplicate file names in the manifest: {duplicates[:5]}")
    classes = sorted({b[0] for r in records for b in r["boxes"]})
    if any(c not in (0, 1, 2, 3) for c in classes):
        problems.append(f"class ids outside 0-3: {classes}")
    most = max((len(r["boxes"]) for r in records), default=0)
    if most > MAX_QUERIES:
        problems.append(f"most crowded image has {most} insects, more than the model's {MAX_QUERIES} queries")
    checked = 0
    if image_sizes is not None:
        for r in records:
            seen = image_sizes.get(r["file"])
            if seen is None:
                problems.append(f"image missing: {r['relative_path']}")
            elif tuple(seen) != (r["width"], r["height"]):
                problems.append(f"{r['file']}: size {seen} != manifest {(r['width'], r['height'])}")
            else:
                checked += 1
    table = {"split_sizes": sizes, "unique_file_names": not duplicates, "class_ids": classes,
             "max_insects_per_image": most, "queries": MAX_QUERIES, "images_size_checked": checked}
    return table, problems


def stage_validate(ctx: Context) -> None:
    from PIL import Image

    manifest = ctx.manifest()
    seen = {}
    for r in manifest["images"]:
        path = ctx.images / r["relative_path"]
        if path.is_file():
            with Image.open(path) as img:
                img.verify()
            with Image.open(path) as img:
                seen[r["file"]] = img.size
    table, problems = validation_problems(manifest, seen)
    write_json(ctx.run_dir / "validate.json", {**table, "problems": problems})
    print("| check | value |\n| :-- | :-- |")
    for key, value in table.items():
        print(f"| {key} | {value} |")
    if problems:
        raise SystemExit("Data validation failed: " + "; ".join(problems[:10]))
    print("data validation: all checks passed")


# ---------------------------------------------------------------- resume


def resume_from(source: str, run_dir: Path) -> dict:
    """Copy an earlier run's files (attached by the reader) into `run_dir`. Empty `source` does nothing."""
    run_dir = Path(run_dir)
    if not source or not str(source).strip():
        print("resume: off (RESUME_FROM is empty); training starts from the base model")
        return {"resumed": False}
    found = sorted(Path(source).rglob("last.pt"))
    if not found:
        raise SystemExit(f"resume: no last.pt found under {source}; attach an earlier run's output or leave "
                         "RESUME_FROM empty")
    origin = found[0].parent
    print("WARNING: a .pt checkpoint is loaded with PyTorch's pickle-based format, so loading it can run code. "
          "Only resume from a run you produced yourself.")
    copied = []
    for name in RESUME_FILES:
        if (origin / name).is_file():
            shutil.copy(origin / name, run_dir / name)
            copied.append(name)
    print("resume: copied", ", ".join(copied), "from", origin)
    record = {"resumed": True, "from": str(origin), "files": copied}
    write_json(run_dir / "resume.json", record)
    return record


def stage_resume(ctx: Context, source: str) -> None:
    resume_from(source, ctx.run_dir)


# ---------------------------------------------------------------- model helpers


def train_config(edition: dict):
    from rice_pest_detector.train import TrainConfig

    extra = {"input_size": edition["input_size"]} if edition["input_size"] != 640 else {}
    return TrainConfig(base_model=edition["base_model"], revision=edition["revision"],
                       batch_size=edition["batch_size"], epochs=edition["epochs"], **extra)


def export_module():
    """`rpd_tools.export_onnx` in the notebook's work folder; the repository's `tools.export_onnx` in tests."""
    try:
        from rpd_tools import export_onnx
    except ModuleNotFoundError as exc:
        if exc.name not in ("rpd_tools", "rpd_tools.export_onnx"):
            raise
        from tools import export_onnx
    return export_onnx


def load_selected(ctx: Context):
    """The selected checkpoint (best.pt) on the architecture rebuilt from the base config, no base weights."""
    if ctx.edition["base_model"] == "__tiny__":  # tests only
        from rice_pest_detector.train import build_model, load_best

        model = build_model(train_config(ctx.edition))
        state, meta = load_best(ctx.run_dir / "best.pt")
        model.load_state_dict(state)
        return model.eval(), meta
    return export_module().load_trained(ctx.run_dir / "best.pt", ctx.edition["base_model"], ctx.edition["revision"])


def device():
    import torch

    return "cuda" if torch.cuda.is_available() else "cpu"


# ---------------------------------------------------------------- fit


def stage_fit(ctx: Context) -> None:
    from rice_pest_detector.train import fit

    cfg = train_config(ctx.edition)
    print("recipe:", json.dumps({k: getattr(cfg, k) for k in ("base_model", "revision", "epochs", "batch_size",
                                                               "lr", "backbone_lr", "input_size", "seed", "fp16")}))
    best = fit(cfg, ctx.manifest(), ctx.images, ctx.run_dir)
    print("selected checkpoint:", best, read_json(ctx.run_dir / "best.json"))


# ---------------------------------------------------------------- evaluate


def evaluate_with_detections(model, dataset, coco: dict, threshold: float) -> tuple[dict, list[dict]]:
    """Run the repository's own `train.evaluate` and keep the raw detections it scores (no second copy)."""
    from rice_pest_detector import train

    captured = []
    original = train.map50

    def capturing(gt, dets, group_species):
        if group_species:
            captured[:] = [dict(d) for d in dets]
        return original(gt, dets, group_species)

    train.map50 = capturing
    try:
        metrics = train.evaluate(model, dataset, coco, threshold=threshold)
    finally:
        train.map50 = original
    return metrics, captured


def headline(metrics: dict) -> dict:
    by_class = {k: v for k, v in metrics["map50_by_class"].items() if k != "all"}
    errors = metrics["count_errors"]
    return {"map50_species": metrics["map50_species"],
            "map50_four_class": sum(by_class.values()) / len(by_class),
            "map50_by_class": by_class,
            "count_accuracy": metrics["count_accuracy"],
            "count_accuracy_no_detection_baseline": metrics["count_accuracy_no_detection_baseline"],
            "mae": {"rbb": errors["RBB"]["mae"], "wsb": errors["WSB"]["mae"]},
            "wsb30_mae": errors["WSB"]["mae_by_density"]["30+"]["mae"],
            "wsb30_images": errors["WSB"]["mae_by_density"]["30+"]["images"]}


def stage_evaluate(ctx: Context) -> None:
    from rice_pest_detector.train import ManifestDataset

    model, meta = load_selected(ctx)
    model = model.to(device())
    threshold = ctx.edition["threshold"]
    dataset = ManifestDataset(ctx.manifest(), ctx.images, split="val", size=ctx.edition["input_size"])
    coco = read_json(ctx.data / "annotations_val.json")
    metrics, dets = evaluate_with_detections(model, dataset, coco, threshold)
    files = {i: r["file"] for i, r in enumerate(dataset.records, start=1)}
    write_json(ctx.run_dir / "val_metrics.json", {**metrics, "headline": headline(metrics), "epoch": meta.get("epoch"),
                                                  "label": "tutorial evidence: one validation pass at the "
                                                           "published threshold"})
    write_json(ctx.run_dir / "val_detections.json",
               {"threshold": threshold, "score_floor": 0.0,
                "images": [{"image_id": i, "file": files[i],
                            "detections": [{k: d[k] for k in ("category_id", "score", "bbox")}
                                           for d in dets if d["image_id"] == i]} for i in files]})
    h = headline(metrics)
    print(f"Validation, one pass at threshold {threshold} (tutorial evidence, not the recorded out-of-fold figure)")
    print(f"  species mAP50 {h['map50_species']:.3f}; four-class mAP50 {h['map50_four_class']:.3f}")
    print("  per class:", ", ".join(f"{k} {v:.3f}" for k, v in h["map50_by_class"].items()))
    print(f"  count accuracy {h['count_accuracy']:.3f} (count-nothing baseline "
          f"{h['count_accuracy_no_detection_baseline']:.3f})")
    print(f"  count MAE RBB {h['mae']['rbb']:.2f}, WSB {h['mae']['wsb']:.2f}; crowded trays (WSB {CROWDED}+, "
          f"{h['wsb30_images']} images) MAE {h['wsb30_mae']}")


# ---------------------------------------------------------------- export and reload


def stage_export(ctx: Context) -> None:
    model, meta = load_selected(ctx)
    info = export_module().export_onnx(model.cpu().eval(), ctx.run_dir / "model.onnx", size=ctx.edition["input_size"])
    info.update(checkpoint_sha256=sha256_file(ctx.run_dir / "best.pt"), checkpoint_epoch=meta.get("epoch"),
                selection="best validation species mAP50", base_model=ctx.edition["base_model"],
                revision=ctx.edition["revision"], input_size=ctx.edition["input_size"])
    write_json(ctx.run_dir / "export_record.json", info)
    print(json.dumps(info, indent=1))


def onnx_detect(model_path: Path, records: list[dict], image_root: Path, size: int, threshold: float) -> list:
    """ONNX Runtime detections per record; used by the fresh `python -I` process and by inference."""
    import onnxruntime as ort
    from PIL import Image, ImageOps

    from rice_pest_detector.infer import postprocess, preprocess

    session = ort.InferenceSession(str(model_path), providers=["CPUExecutionProvider"])
    out = []
    for r in records:
        with Image.open(Path(image_root) / r["relative_path"]) as img:
            width, height = ImageOps.exif_transpose(img).size
            x = preprocess(img, size)
        logits, boxes = session.run(["logits", "pred_boxes"], {"pixel_values": x})
        out.append([d.__dict__ for d in postprocess(logits, boxes, width, height, threshold)])
    return out


def torch_detect(model, records: list[dict], image_root: Path, size: int, threshold: float) -> list:
    import torch
    from PIL import Image, ImageOps

    from rice_pest_detector.infer import postprocess, preprocess

    model = model.cpu().eval()
    out = []
    for r in records:
        with Image.open(Path(image_root) / r["relative_path"]) as img:
            width, height = ImageOps.exif_transpose(img).size
            x = preprocess(img, size)
        with torch.no_grad():
            ref = model(pixel_values=torch.from_numpy(x))
        out.append([d.__dict__ for d in postprocess(ref.logits.float().numpy(), ref.pred_boxes.float().numpy(),
                                                    width, height, threshold)])
    return out


def compare_detections(onnx_dets: list, torch_dets: list, score_tolerance_enforced: bool) -> dict:
    """`parity()`'s pairing and tolerances, applied per photo; returns the report with its verdict."""
    from rice_pest_detector.infer import Detection
    ex = export_module()
    IOU_MIN, SCORE_DIFF_MAX, _iou, _pair = ex.IOU_MIN, ex.SCORE_DIFF_MAX, ex._iou, ex._pair

    photos, failures, compared, max_score, min_iou = [], [], 0, 0.0, 1.0
    for i, (a_raw, b_raw) in enumerate(zip(onnx_dets, torch_dets, strict=True)):
        a, b = [Detection(**d) for d in a_raw], [Detection(**d) for d in b_raw]
        pairs = _pair(a, b)
        if pairs is None:
            failures.append({"photo": i, "check": "kept detections",
                             "detail": f"ONNX kept {len(a)}, PyTorch kept {len(b)}, or classes differ"})
            photos.append({"photo": i, "onnx": len(a), "torch": len(b), "paired": False})
            continue
        score = max((abs(x.score - y.score) for x, y in pairs), default=0.0)
        iou = min((_iou(x, y) for x, y in pairs), default=1.0)
        compared += len(pairs)
        max_score, min_iou = max(max_score, score), min(min_iou, iou)
        photos.append({"photo": i, "onnx": len(a), "torch": len(b), "paired": True,
                       "max_score_diff": score, "min_iou": iou})
        if iou < IOU_MIN:
            failures.append({"photo": i, "check": "box overlap", "detail": f"min IoU {iou:.4f} < {IOU_MIN}"})
        if score > SCORE_DIFF_MAX:
            entry = {"photo": i, "check": "score difference", "detail": f"{score:.2e} > {SCORE_DIFF_MAX}"}
            (failures if score_tolerance_enforced else photos[-1].setdefault("waived", [])).append(entry)
    return {"photos": len(photos), "detections_compared": compared, "max_score_diff": max_score,
            "min_iou": min_iou, "iou_min": IOU_MIN, "score_diff_max": SCORE_DIFF_MAX,
            "score_tolerance_enforced": score_tolerance_enforced, "per_photo": photos, "failures": failures,
            "verdict": "FAIL" if failures else "PASS"}


def judge_reload(report: dict) -> None:
    if report["failures"]:
        first = report["failures"][0]
        raise RuntimeError(f"fresh-process ONNX reload check failed: {first['check']} on photo {first['photo']} "
                           f"({first['detail']}); {len(report['failures'])} failure(s) in reload_check.json")


def stage_reload(ctx: Context) -> None:
    import subprocess

    records = ctx.records("val")[:RELOAD_PHOTOS]
    size, threshold = ctx.edition["input_size"], ctx.edition["threshold"]
    model, _ = load_selected(ctx)
    torch_dets = torch_detect(model, records, ctx.images, size, threshold)
    onnx_out = ctx.run_dir / "reload_onnx_detections.json"
    # A fresh, isolated interpreter (-I) that loads only model.onnx: nothing from this process carries over.
    subprocess.run([sys.executable, "-I", str(Path(__file__).resolve()), "--stage", "onnx-detect",
                    "--work", str(ctx.work), "--run-dir", str(ctx.run_dir), str(onnx_out)], check=True)
    onnx_dets = read_json(onnx_out)
    report = compare_detections(onnx_dets, torch_dets, ctx.edition["score_tolerance_enforced"])
    report.update(threshold=threshold, files=[r["file"] for r in records],
                  waiver=ctx.edition.get("score_waiver"))
    write_json(ctx.run_dir / "reload_check.json", report)
    print(f"fresh-process ONNX reload check: {report['detections_compared']} detections on {report['photos']} "
          f"photos; max score difference {report['max_score_diff']:.2e}; min box IoU {report['min_iou']:.5f}; "
          f"score tolerance {'enforced' if report['score_tolerance_enforced'] else 'waived: ' + str(report['waiver'])}")
    judge_reload(report)
    print("reload check: PASS (the ONNX file loaded from disk in a fresh process gives the same kept detections)")


def stage_onnx_detect(ctx: Context, out: str) -> None:
    records = ctx.records("val")[:RELOAD_PHOTOS]
    dets = onnx_detect(ctx.run_dir / "model.onnx", records, ctx.images, ctx.edition["input_size"],
                       ctx.edition["threshold"])
    write_json(Path(out), dets)


# ---------------------------------------------------------------- inference


def review_reason(scores: list[float], review_below: float, crowded: int = CROWDED) -> str:
    reasons = []
    if any(s < review_below for s in scores):
        reasons.append(f"a counted insect scored below {review_below}")
    if len(scores) > crowded:
        reasons.append(f"more than {crowded} insects")
    return "; ".join(reasons)


def stage_inference(ctx: Context) -> None:
    from rice_pest_detector import SPECIES_OF_CLASS

    lo, hi = INFERENCE_PHOTOS
    records = ctx.records("val")[lo:hi]
    dets = onnx_detect(ctx.run_dir / "model.onnx", records, ctx.images, ctx.edition["input_size"],
                       ctx.edition["threshold"])
    rows = []
    for r, found in zip(records, dets, strict=True):
        pred = [SPECIES_OF_CLASS[d["class_id"]] for d in found]
        true = [SPECIES_OF_CLASS[b[0]] for b in r["boxes"]]
        reason = review_reason([d["score"] for d in found], ctx.edition["review_below"])
        rows.append({"file": r["file"], "pred_rbb": pred.count("RBB"), "pred_wsb": pred.count("WSB"),
                     "true_rbb": true.count("RBB"), "true_wsb": true.count("WSB"),
                     "review_flag": bool(reason), "review_reason": reason})
    with (ctx.run_dir / "predictions_val_sample.csv").open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    for row in rows:
        print(row)


# ---------------------------------------------------------------- test look


def stage_test_look(ctx: Context) -> None:
    from rice_pest_detector.train import (
        ManifestDataset,
        _atomic_write_text,
        check_cached_test,
        evaluate,
        evaluation_id,
    )

    threshold = ctx.edition["threshold"]  # the published threshold, from the model's manifest
    coco_path = ctx.data / "annotations_test.json"
    best, manifest = ctx.run_dir / "best.pt", ctx.manifest()
    identity = evaluation_id(best, manifest, coco_path, threshold)
    out = ctx.run_dir / "test_metrics_reproduction.json"
    print("The test split's looks are spent; this is a reproduction and must not be used to choose anything.")
    if out.exists():
        prior = read_json(out)
        check_cached_test(prior, identity)
        print(json.dumps(prior, indent=1))
        return
    model, meta = load_selected(ctx)
    test_set = ManifestDataset(manifest, ctx.images, split="test", size=ctx.edition["input_size"])
    metrics = evaluate(model.to(device()), test_set, read_json(coco_path), threshold=threshold)
    metrics = {**metrics, "label": "reproduction of an already-spent test look; not for choosing anything",
               "best_pt_sha256": identity["best_pt_sha256"], "epoch": meta.get("epoch"), "evaluation": identity}
    _atomic_write_text(out, json.dumps(metrics, indent=1))
    print(json.dumps(metrics, indent=1))


# ---------------------------------------------------------------- env log and summary


def versions() -> dict:
    import numpy
    import onnxruntime
    import PIL
    import torch
    import transformers

    cuda = torch.cuda.is_available()
    return {"python": platform.python_version(), "torch": torch.__version__, "cuda": torch.version.cuda,
            "transformers": transformers.__version__, "pillow": PIL.__version__, "numpy": numpy.__version__,
            "onnxruntime": onnxruntime.__version__,
            "gpu": torch.cuda.get_device_name(0) if cuda else None,
            "gpu_count": torch.cuda.device_count() if cuda else 0}


def stage_env_log(ctx: Context) -> None:
    from importlib import metadata

    stamp = datetime.datetime.now(datetime.UTC).strftime("%Y%m%dT%H%M%SZ")
    v = versions()
    freeze = sorted(f"{d.metadata['Name']}=={d.version}" for d in metadata.distributions())
    lines = [f"utc: {stamp}", f"python: {sys.version}", *(f"{k}: {val}" for k, val in v.items()),
             "--- packages in the environment ---", *freeze]
    (ctx.run_dir / f"env-{stamp}.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps(v, indent=1))
    print("environment log written to", f"env-{stamp}.txt")


def output_listing(run_dir: Path) -> tuple[list[tuple[str, int]], int, list[str]]:
    """Every file under `run_dir` with its size, the total, and problems (budget, images, archives)."""
    run_dir = Path(run_dir)
    files = sorted((p.relative_to(run_dir).as_posix(), p.stat().st_size) for p in run_dir.rglob("*") if p.is_file())
    total = sum(size for _, size in files)
    problems = [f"image file in the output: {name}" for name, _ in files if name.lower().endswith(IMAGE_SUFFIXES)]
    problems += [f"archive in the output: {name}" for name, _ in files if name.lower().endswith(ARCHIVE_SUFFIXES)]
    if total > OUTPUT_BUDGET_BYTES:
        problems.append(f"outputs total {total / 1e9:.2f} GB, over the {OUTPUT_BUDGET_BYTES / 1e9:.0f} GB budget")
    return files, total, problems


def _artifact(path: Path) -> dict:
    return {"bytes": path.stat().st_size, "sha256": sha256_file(path)} if path.is_file() else None


def build_summary(ctx: Context, runtime: dict) -> dict:
    run = ctx.run_dir
    files, total, problems = output_listing(run)
    if problems:
        raise RuntimeError("output check failed: " + "; ".join(problems))
    times = read_json(run / "stage_times.json") if (run / "stage_times.json").exists() else {}
    history = [json.loads(ln) for ln in (run / "history.jsonl").read_text().splitlines() if ln.strip()]
    best = read_json(run / "best.json")
    resume = read_json(run / "resume.json") if (run / "resume.json").exists() else {"resumed": False}
    val = read_json(run / "val_metrics.json")["headline"]
    reload_check = read_json(run / "reload_check.json")
    lock = ctx.work / LOCK_NAME
    durations = {k: times.get(k) for k in ("environment", "fetch", "fit", "evaluate", "export", "reload")}
    durations["total"] = round(sum(v for v in times.values() if isinstance(v, (int, float))), 1)
    return {
        "schema": 1, "status": "PASS", "variant": ctx.edition["variant"],
        "model": {k: ctx.edition[k] for k in ("base_model", "revision", "threshold", "input_size")},
        "environment": {"uv": UV_VERSION, "lock_sha256": sha256_file(lock) if lock.exists() else None,
                        "build_seconds": times.get("environment")},
        "runtime": runtime, "durations_s": durations,
        "training": {"epochs": ctx.edition["epochs"], "epochs_run_this_session": len(history) if not
                     resume["resumed"] else None, "resumed": resume["resumed"], "best_epoch": best["epoch"],
                     "best_val_map50_species": best["map50_species"],
                     "skipped_updates_total": sum(r.get("skipped_updates", 0) for r in history)},
        "validation": val,
        "artifacts": {name: _artifact(run / name) for name in ("best.pt", "model.onnx")},
        "reload_check": {"photos": reload_check["photos"], "detections_compared": reload_check["detections_compared"],
                         "max_score_diff": reload_check["max_score_diff"], "min_iou": reload_check["min_iou"],
                         "score_tolerance_enforced": reload_check["score_tolerance_enforced"],
                         "verdict": reload_check["verdict"]},
        "outputs_total_bytes": total,
        "outputs": [{"file": name, "bytes": size} for name, size in files],
        "test_look": "ran (reproduction)" if (run / "test_metrics_reproduction.json").exists() else "skipped",
    }


def stage_summary(ctx: Context) -> None:
    summary = build_summary(ctx, versions())
    write_json(ctx.run_dir / "run_summary.json", summary)
    v, t, r = summary["validation"], summary["training"], summary["reload_check"]
    onnx = summary["artifacts"]["model.onnx"]
    print(f"Run summary: {summary['variant']} ({summary['model']['base_model']}), status {summary['status']}")
    print(f"  GPU {summary['runtime']['gpu']}; torch {summary['runtime']['torch']}; "
          f"transformers {summary['runtime']['transformers']}")
    print(f"  best epoch {t['best_epoch']} (validation species mAP50 {t['best_val_map50_species']:.3f})")
    print(f"  validation at {summary['model']['threshold']}: species mAP50 {v['map50_species']:.3f}, count accuracy "
          f"{v['count_accuracy']:.3f} (baseline {v['count_accuracy_no_detection_baseline']:.3f})")
    print(f"  model.onnx {onnx['bytes']:,} bytes, SHA-256 {onnx['sha256']}")
    print(f"  fresh-process ONNX reload check: {r['verdict']} ({r['detections_compared']} detections, "
          f"max score difference {r['max_score_diff']:.2e}, min IoU {r['min_iou']:.5f})")
    print(f"  test split: {summary['test_look']}")
    print(f"  outputs: {summary['outputs_total_bytes'] / 1e9:.2f} GB in {ctx.run_dir}")
    for item in summary["outputs"]:
        print(f"    {item['bytes']:>14,}  {item['file']}")


STAGES = {"fetch": stage_fetch, "validate": stage_validate, "fit": stage_fit, "evaluate": stage_evaluate,
          "export": stage_export, "reload": stage_reload, "inference": stage_inference,
          "test-look": stage_test_look, "summary": stage_summary, "env-log": stage_env_log}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--stage", required=True, choices=sorted([*STAGES, "resume", "onnx-detect"]))
    parser.add_argument("--work", type=Path, required=True)
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--input-root", type=Path, default=Path("/kaggle/input"))
    parser.add_argument("options", nargs="*")
    args = parser.parse_args(argv)
    sys.path.insert(0, str(args.work))  # the carried package and rpd_tools, written by the notebook
    os.environ.setdefault("HF_HUB_DISABLE_TELEMETRY", "1")
    ctx = Context(args.work, args.run_dir, args.input_root)
    started = time.time()
    if args.stage == "resume":
        stage_resume(ctx, args.options[0] if args.options else "")
    elif args.stage == "onnx-detect":
        stage_onnx_detect(ctx, args.options[0])
    else:
        STAGES[args.stage](ctx)
    print(f"[{args.stage}] done in {time.time() - started:.1f} s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
