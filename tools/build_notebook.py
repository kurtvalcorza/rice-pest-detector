"""Generate notebooks/train_colab.ipynb from the package sources (never hand-edit the notebook)."""

import argparse
import base64
import gzip
import io
import sys
import textwrap
from pathlib import Path

import nbformat
from nbformat.v4 import new_code_cell, new_markdown_cell, new_notebook

ROOT = Path(__file__).resolve().parents[1]

FETCH_SOURCE = """\
import sys, json, shutil, hashlib
sys.path.insert(0, '/content/rpd')
from pathlib import Path
from rice_pest_detector import fetch
dest = Path('/content/datasets.zip')
def _pins_ok(p):
    if not p.exists() or p.stat().st_size != fetch.ZENODO_BYTES:
        return False
    md5, sha = hashlib.md5(), hashlib.sha256()
    with p.open('rb') as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b''):
            md5.update(chunk)
            sha.update(chunk)
    return md5.hexdigest() == fetch.ZENODO_MD5 and sha.hexdigest() == fetch.ZENODO_SHA256
drive_copy = Path('/content/drive/MyDrive/rice-pest-detector/datasets.zip')
if _pins_ok(dest):
    archive = dest
    print('verified archive present, skipping download')
elif drive_copy.exists():  # fallback copy, verified with the same pins
    archive = fetch.download(drive_copy.as_uri(), dest, fetch.ZENODO_BYTES, fetch.ZENODO_MD5, fetch.ZENODO_SHA256)
else:
    archive = fetch.download(fetch.ZENODO_URL, dest, fetch.ZENODO_BYTES, fetch.ZENODO_MD5, fetch.ZENODO_SHA256)
manifest = json.loads(Path('/content/rpd/data/split_manifest.json').read_text())
print(fetch.extract_members(archive, manifest, Path('/content/data')), 'images verified')
shutil.copy('/content/rpd/data/annotations_val.json', RUN_DIR)"""

DRIVE_SOURCE = """\
import os, shutil
from google.colab import drive
drive.mount('/content/drive')
RUN_DIR = '/content/drive/MyDrive/rice-pest-detector/run-r18'
os.makedirs(RUN_DIR, exist_ok=True)
free_gb = shutil.disk_usage('/content/drive').free / 1e9
print(f'Drive free space: {free_gb:.1f} GB')
if free_gb < 20:
    print('WARNING: less than 20 GB free on Drive; checkpoints may fail to save. Free space first.')"""

ENV_LOG_SOURCE = """\
import subprocess, sys, datetime
from pathlib import Path
import torch, transformers
stamp = datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ')
def _run(*cmd):
    done = subprocess.run(cmd, capture_output=True, text=True)
    return done.stdout + done.stderr
log = '\\n'.join([
    f'utc: {stamp}',
    f'python: {sys.version}',
    f'torch: {torch.__version__} (cuda {torch.version.cuda})',
    f'transformers: {transformers.__version__}',
    '--- nvidia-smi ---', _run('nvidia-smi'),
    '--- pip freeze ---', _run(sys.executable, '-m', 'pip', 'freeze'),
])
Path(RUN_DIR, f'env-{stamp}.txt').write_text(log)
print('environment log written to', f'env-{stamp}.txt')"""
TEST_EVAL_SOURCE = """\
from rice_pest_detector.train import (ManifestDataset, build_model, check_cached_test, evaluate,
                                      evaluation_id, load_best)
THRESHOLD = 0.5
test_coco_path = Path('/content/rpd/data/annotations_test.json')
identity = evaluation_id(best, manifest, test_coco_path, THRESHOLD)
metrics_path = Path(RUN_DIR, 'test_metrics.json')
if metrics_path.exists():
    prior = json.loads(metrics_path.read_text())
    print(json.dumps(prior, indent=1))
    check_cached_test(prior, identity)
    print('test split already evaluated for this checkpoint and setup')
else:
    state, meta = load_best(best)
    model = build_model(cfg)
    model.load_state_dict(state)
    model = model.cuda()
    test_set = ManifestDataset(manifest, Path("/content/data"), split="test")
    metrics = evaluate(model, test_set, json.loads(test_coco_path.read_text()), threshold=THRESHOLD)
    metrics = {**metrics, 'best_pt_sha256': identity['best_pt_sha256'], 'epoch': meta['epoch'],
               'evaluation': identity}
    print(json.dumps(metrics, indent=1))
    metrics_path.write_text(json.dumps(metrics, indent=1))"""


def _cell(factory, cell_id: str, source: str):
    cell = factory(source)
    cell["id"] = cell_id  # fixed ids keep the generated file byte-reproducible for --check
    return cell


def _writefile(cell_id: str, target: str, path: Path):
    return _cell(new_code_cell, cell_id, f"%%writefile {target}\n" + path.read_text(encoding="utf-8"))


def _data_cell(cell_id: str, path: Path):
    buf = io.BytesIO()
    with gzip.GzipFile(fileobj=buf, mode="wb", compresslevel=9, mtime=0) as gz:
        gz.write(path.read_bytes())
    packed = bytearray(buf.getvalue())
    packed[9] = 255  # fixed OS byte: identical output on every platform
    b64 = "\n".join(textwrap.wrap(base64.b64encode(bytes(packed)).decode("ascii"), 100))
    source = (
        "import base64, gzip, pathlib\n"
        f'B64 = """\n{b64}\n"""\n'
        f"pathlib.Path('/content/rpd/data/{path.name}').write_bytes("
        "gzip.decompress(base64.b64decode(''.join(B64.split()))))"
    )
    return _cell(new_code_cell, cell_id, source)


# Run variants. r18 is run r18-1 and must stay byte-identical (build_notebook --check).
# r50 is the spec's fallback (owner decision 2026-10-16): same contract at 640x640, batch 4 to fit
# a T4's 16 GB, 40 epochs (r18 peaked at epoch 3 of 60), and its own Drive folder.
VARIANTS = {
    "r18": {"model": "PekingU/rtdetr_r18vd", "title": "RT-DETR-r18vd", "run": "run-r18", "config": ""},
    "r50": {"model": "PekingU/rtdetr_r50vd", "title": "RT-DETR-r50vd", "run": "run-r50",
            "config": ", batch_size=4, epochs=40"},
    # Wave 2 (owner, 2026-10-17): transformers >= 5.18 fixes the main loss being computed over the
    # denoising queries (PR #48528). Same recipe as r50-1 so the runs compare fairly.
    "r50v5": {"model": "PekingU/rtdetr_r50vd", "title": "RT-DETR-r50vd on transformers 5.20.1",
              "run": "run-r50v5", "config": ", batch_size=4, epochs=40", "transformers": "5.20.1"},
    "dfine-l": {"model": "ustc-community/dfine-large-coco", "title": "D-FINE-L (COCO weights)",
                "run": "run-dfine-l", "config": ", batch_size=4, epochs=40", "transformers": "5.20.1"},
    # RF-DETR-M (Apache-2.0 for N/S/M/L) at its native 576 px; the 640 app contract changes only if it wins.
    "rfdetr-m": {"model": "Roboflow/rf-detr-medium", "title": "RF-DETR-M at 576 px", "run": "run-rfdetr-m",
                 "config": ", batch_size=4, epochs=40, input_size=576", "transformers": "5.20.1",
                 "input_size": 576},
}

# The r50 test look is a one-time owner exception (docs/evaluation-record.md): it runs only after the
# checkpoint, threshold and calibration are fixed on validation, so the threshold must be set by hand.
TEST_GATE_SOURCE = """\
THRESHOLD = None  # set to the threshold chosen on VALIDATION (see docs/evaluation-record.md), then run
if THRESHOLD is None:
    raise RuntimeError('Test look not unlocked: choose the threshold on validation first, then set THRESHOLD.')
"""

# The notebook embeds labels derived from the dataset, so it carries the dataset's credit.
DATA_CREDIT = ("Data: Deleña, R.; Balleras, G.; Dequiña, B. J.; Jumawan, R.; Flores, C. *Annotated light-trap rice pest "
               "image dataset with detector-derived region-of-interest crops for species-sex recognition of rice black "
               "bug and white stemborer.* Version 1. Zenodo. "
               "[doi:10.5281/zenodo.20066074](https://doi.org/10.5281/zenodo.20066074). Licence: "
               "[CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). The embedded labels are derived from it; "
               "changes are listed in `data/README.md`.")
# These variants were run, and their notebooks' SHA-256 values recorded, before the credit was added. They are
# built without it so that `--check` still matches the committed files. Every later variant carries the credit.
BUILT_BEFORE_CREDIT = {"r18", "r50", "r50v5", "dfine-l", "rfdetr-m"}


def build(out: Path, revision: str, variant: str = "r18") -> Path:
    v = VARIANTS[variant]
    test_source = TEST_EVAL_SOURCE
    if variant != "r18":  # review 2026-10-17 (m1, m2): check before showing numbers; write atomically
        for old, new in (
            ("THRESHOLD = 0.5\n", TEST_GATE_SOURCE),
            ("evaluation_id, load_best)", "evaluation_id, load_best, _atomic_write_text)"),
            ("    print(json.dumps(prior, indent=1))\n    check_cached_test(prior, identity)\n",
             "    check_cached_test(prior, identity)\n    print(json.dumps(prior, indent=1))\n"),
            ("    metrics_path.write_text(json.dumps(metrics, indent=1))",
             "    _atomic_write_text(metrics_path, json.dumps(metrics, indent=1))"),
        ):
            assert test_source.count(old) == 1, old
            test_source = test_source.replace(old, new)
    if "input_size" in v:  # non-640 models must see test images at their own input size
        old = 'split="test")'
        assert test_source.count(old) == 1, old
        test_source = test_source.replace(old, 'split="test", size=cfg.input_size)')
    drive_source = DRIVE_SOURCE.replace("/run-r18'", f"/{v['run']}'")
    if variant != "r18":  # headless runs mount Drive with `colab drivemount` first; don't sign in twice
        drive_source = drive_source.replace(
            "drive.mount('/content/drive')",
            "if not os.path.isdir('/content/drive/MyDrive'):\n    drive.mount('/content/drive')")
    intro = (f"# Rice-pest detector — {v['title']} fine-tune (Colab T4)\n"
             "Generated by `tools/build_notebook.py`. Runtime: T4 GPU. Run all; re-running "
             "after a disconnect resumes from Drive.")
    if variant not in BUILT_BEFORE_CREDIT:
        intro += "\n\n" + DATA_CREDIT
    cells = [
        _cell(new_markdown_cell, "intro", intro),
        _cell(new_code_cell, "drive", drive_source),
        _cell(new_code_cell, "env",
              "!nvidia-smi\nimport torch, sys\nprint(sys.version, torch.__version__, torch.version.cuda)\n"
              f"!pip -q install transformers=={v.get('transformers', '4.57.6')} pycocotools scipy"),
        _cell(new_code_cell, "versions",
              "import transformers\nprint('transformers', transformers.__version__)\n"
              "if not torch.cuda.is_available():\n"
              "    raise RuntimeError('No GPU: choose Runtime > Change runtime type > T4 GPU, then Run all')"),
        _cell(new_code_cell, "env-log", ENV_LOG_SOURCE),
        _cell(new_code_cell, "dirs",
              "import os\nos.makedirs('/content/rpd/rice_pest_detector', exist_ok=True)\n"
              "os.makedirs('/content/rpd/data', exist_ok=True)"),
    ]
    for i, module in enumerate(sorted((ROOT / "src" / "rice_pest_detector").glob("*.py"))):
        cells.append(_writefile(f"module-{i:02d}", f"/content/rpd/rice_pest_detector/{module.name}", module))
    for i, data in enumerate(sorted((ROOT / "data").glob("*.json"))):
        cells.append(_data_cell(f"data-{i:02d}", data))
    cells += [
        _cell(new_code_cell, "fetch", FETCH_SOURCE),
        _cell(new_code_cell, "fit",
              "from rice_pest_detector.train import TrainConfig, fit\n"
              f'cfg = TrainConfig(base_model="{v["model"]}", revision="{revision}"{v["config"]})\n'
              "best = fit(cfg, manifest, Path('/content/data'), Path(RUN_DIR))\nprint(best)"),
        _cell(new_code_cell, "test-eval", test_source),
    ]
    nb = new_notebook(cells=cells, metadata={"accelerator": "GPU", "colab": {"gpuType": "T4"}})
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", encoding="utf-8", newline="\n") as fh:
        nbformat.write(nb, fh)
    return out


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--revision", required=True)
    parser.add_argument("--variant", choices=sorted(VARIANTS), default="r18")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    name = "train_colab.ipynb" if args.variant == "r18" else f"train_colab_{args.variant}.ipynb"
    target = ROOT / "notebooks" / name
    if args.check:
        fresh = build(ROOT / "runs" / "check.ipynb", args.revision, args.variant)
        sys.exit(0 if fresh.read_bytes() == target.read_bytes() else 1)
    print(build(target, args.revision, args.variant))


if __name__ == "__main__":
    main()
