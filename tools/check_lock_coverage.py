"""Show that the Kaggle editions' lock covers every run-time import (spec 010, FR-030, ENV14).

Builds a Python 3.12.12 environment from the hash lock alone with the pinned uv 0.12.15, writes the carried files
into a work folder the way the notebook does, and runs the driver's fit, evaluate, export, reload and summary stages
on CPU with a tiny untrained RT-DETR and a few synthetic images. Run it on Linux x86_64 (WSL or a CI runner) before
the first push and after any lock change:

    python tools/check_lock_coverage.py notebooks/kaggle/requirements-kaggle.lock.txt --uv <path to uv 0.12.15>

`--python <interpreter>` skips the build and runs the stages with an existing interpreter (a check of this script
itself, not of the lock). Exit 0 when every stage passes.
"""

import argparse
import os
import platform
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
UV_VERSION = "0.12.15"
PYTHON_VERSION = "3.12.12"

HARNESS = r'''
import json, sys
from pathlib import Path
work, run = Path(sys.argv[1]), Path(sys.argv[2])
sys.path.insert(0, str(work))
import numpy as np
from PIL import Image
from transformers import RTDetrConfig
import kaggle_driver as kd
import rice_pest_detector.train as train

train._tiny_config = lambda: RTDetrConfig(
    num_labels=4, num_queries=300, encoder_layers=1, decoder_layers=1, d_model=32, encoder_hidden_dim=32,
    decoder_in_channels=[32, 32, 32], use_pretrained_backbone=False, initializer_range=0.2)
rng = np.random.default_rng(0)
records, coco = [], {"images": [], "annotations": [], "categories": [{"id": i + 1, "name": n} for i, n in
                     enumerate(("RBB_FEMALE", "RBB_MALE", "WSB_FEMALE", "WSB_MALE"))]}
for split, n in (("train", 4), ("val", kd.RELOAD_PHOTOS)):
    for i in range(n):
        rel = f"{split}/img{i}.png"
        (work / "images" / split).mkdir(parents=True, exist_ok=True)
        Image.fromarray(rng.integers(0, 255, (64, 64, 3), dtype="uint8")).save(work / "images" / rel)
        rec = {"file": f"{split}{i}.png", "relative_path": rel, "split": split, "width": 64, "height": 64,
               "boxes": [[i % 4, 0.5, 0.5, 0.2, 0.2]]}
        records.append(rec)
        if split == "val":
            coco["images"].append({"id": i + 1, "file_name": rec["file"], "width": 64, "height": 64})
            coco["annotations"].append({"id": i + 1, "image_id": i + 1, "category_id": i % 4 + 1,
                                        "bbox": [25.6, 25.6, 12.8, 12.8], "area": 163.84, "iscrowd": 0})
(work / "data").mkdir(exist_ok=True)
(work / "data" / "split_manifest.json").write_text(json.dumps({"images": records}))
(work / "data" / "annotations_val.json").write_text(json.dumps(coco))
(run / "annotations_val.json").write_text(json.dumps(coco))
(work / "edition.json").write_text(json.dumps({
    "variant": "lock-coverage", "base_model": "__tiny__", "revision": "none", "input_size": 640, "threshold": 0.0,
    "review_below": 0.5, "epochs": 1, "batch_size": 2, "score_tolerance_enforced": True, "score_waiver": None}))
ctx = kd.Context(work, run)
cfg = kd.train_config(ctx.edition)
cfg.num_workers = 0
train.fit(cfg, ctx.manifest(), ctx.images, run)
for stage in (kd.stage_evaluate, kd.stage_export, kd.stage_reload, kd.stage_env_log):
    stage(ctx)
print(json.dumps(kd.build_summary(ctx, kd.versions())["reload_check"]))
print("LOCK COVERAGE: fit, evaluate, export, reload and summary passed")
'''


def _run(cmd: list[str], env: dict) -> None:
    print("+", " ".join(cmd), flush=True)
    subprocess.run(cmd, env=env, check=True)


def build_env(lock: Path, uv: str, work: Path, env: dict) -> str:
    version = subprocess.run([uv, "--version"], capture_output=True, text=True, check=True).stdout.split()[1]
    if version != UV_VERSION:
        raise SystemExit(f"uv {version} found; the lock is built and installed with uv {UV_VERSION}")
    _run([uv, "venv", "--managed-python", "--python", PYTHON_VERSION, str(work / "env")], env)
    python = str(work / "env" / "bin" / "python")
    _run([uv, "pip", "install", "--python", python, "--require-hashes", "--only-binary", ":all:",
          "--index-url", "https://pypi.org/simple", "-r", str(lock)], env)
    return python


def carry(work: Path) -> None:
    """Write the carried files as the notebook does (package, rpd_tools/export_onnx.py, driver)."""
    shutil.copytree(ROOT / "src" / "rice_pest_detector", work / "rice_pest_detector",
                    ignore=shutil.ignore_patterns("__pycache__"))
    (work / "rpd_tools").mkdir()
    shutil.copy(ROOT / "tools" / "export_onnx.py", work / "rpd_tools" / "export_onnx.py")
    shutil.copy(ROOT / "tools" / "kaggle_driver.py", work / "kaggle_driver.py")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("lock", type=Path)
    ap.add_argument("--uv", default="uv", help="uv 0.12.15 executable")
    ap.add_argument("--python", help="use this interpreter instead of building the environment")
    ap.add_argument("--keep", action="store_true", help="keep the work folder")
    args = ap.parse_args(argv)
    if args.python is None and (platform.system() != "Linux" or platform.machine() != "x86_64"):
        raise SystemExit("the lock targets Linux x86_64: run this on Linux x86_64 (WSL or a CI runner)")
    work = Path(tempfile.mkdtemp(prefix="rpd-lock-"))
    env = {k: v for k, v in os.environ.items()
           if k not in ("PYTHONPATH", "PYTHONHOME", "PYTHONSTARTUP", "HF_TOKEN", "HUGGING_FACE_HUB_TOKEN")}
    env.update(CUDA_VISIBLE_DEVICES="-1", HF_HUB_DISABLE_TELEMETRY="1", DO_NOT_TRACK="1")
    try:
        python = args.python or build_env(args.lock.resolve(), args.uv, work, env)
        carry(work)
        (work / "run").mkdir()
        (work / "harness.py").write_text(HARNESS, encoding="utf-8")
        _run([python, "-I", str(work / "harness.py"), str(work), str(work / "run")], env)
    finally:
        if not args.keep:
            shutil.rmtree(work, ignore_errors=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
