"""Generate the training notebooks from the package sources (never hand-edit a notebook).

Colab variants write `notebooks/train_colab*.ipynb`; Kaggle variants write `notebooks/kaggle/<slug>/` (the notebook,
`kernel-metadata.json` and `declaration.json`). `--check-all` rebuilds every committed notebook and compares.
"""

import argparse
import base64
import gzip
import hashlib
import io
import json
import pprint
import re
import sys
import tempfile
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


def _data_cell(cell_id: str, path: Path, root: str = "/content/rpd"):
    buf = io.BytesIO()
    with gzip.GzipFile(fileobj=buf, mode="wb", compresslevel=9, mtime=0) as gz:
        gz.write(path.read_bytes())
    packed = bytearray(buf.getvalue())
    packed[9] = 255  # fixed OS byte: identical output on every platform
    b64 = "\n".join(textwrap.wrap(base64.b64encode(bytes(packed)).decode("ascii"), 100))
    source = (
        "import base64, gzip, pathlib\n"
        f'B64 = """\n{b64}\n"""\n'
        f"pathlib.Path('{root}/data/{path.name}').write_bytes("
        "gzip.decompress(base64.b64decode(''.join(B64.split()))))"
    )
    return _cell(new_code_cell, cell_id, source)


# Run variants. r18 is run r18-1 and must stay byte-identical (build_notebook --check).
# r50 is the spec's fallback (owner decision 2026-10-16): same contract at 640x640, batch 4 to fit
# a T4's 16 GB, 40 epochs (r18 peaked at epoch 3 of 60), and its own Drive folder.
VARIANTS = {
    "r18": {"model": "PekingU/rtdetr_r18vd", "title": "RT-DETR-r18vd", "run": "run-r18", "config": "",
            "revision": "ac77a11ff0170a41b771c03264987f8ce2b0d753"},
    "r50": {"model": "PekingU/rtdetr_r50vd", "title": "RT-DETR-r50vd", "run": "run-r50",
            "config": ", batch_size=4, epochs=40", "revision": "df939e661d8c52e80608d1ec566561aabd25a4e7"},
    # Wave 2 (owner, 2026-10-17): transformers >= 5.18 fixes the main loss being computed over the
    # denoising queries (PR #48528). Same recipe as r50-1 so the runs compare fairly.
    "r50v5": {"model": "PekingU/rtdetr_r50vd", "title": "RT-DETR-r50vd on transformers 5.20.1",
              "run": "run-r50v5", "config": ", batch_size=4, epochs=40", "transformers": "5.20.1",
              "revision": "df939e661d8c52e80608d1ec566561aabd25a4e7"},
    "dfine-l": {"model": "ustc-community/dfine-large-coco", "title": "D-FINE-L (COCO weights)",
                "run": "run-dfine-l", "config": ", batch_size=4, epochs=40", "transformers": "5.20.1",
                "revision": "aa8f8211545e4cff5adf52ea512f9ac74a9824ec"},
    # RF-DETR-M (Apache-2.0 for N/S/M/L) at its native 576 px; the 640 app contract changes only if it wins.
    "rfdetr-m": {"model": "Roboflow/rf-detr-medium", "title": "RF-DETR-M at 576 px", "run": "run-rfdetr-m",
                 "config": ", batch_size=4, epochs=40, input_size=576", "transformers": "5.20.1",
                 "input_size": 576, "revision": "1b5b672408f86dd38e05dd3cf3f2e0834e545a59"},
}

COLAB_VARIANTS = ("r18", "r50", "r50v5", "dfine-l", "rfdetr-m")

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

# Kaggle editions (spec 010): reference notebooks that run the published recipe end to end on a Kaggle T4. They reuse
# the Colab variant's model, revision and recipe; the threshold, review level and input size come from the manifest.
KAGGLE_OWNER = "kurtvalcorza"
KAGGLE_DIR = ROOT / "notebooks" / "kaggle"
LOCK_PATH = KAGGLE_DIR / "requirements-kaggle.lock.txt"
D_FINE_WAIVER = ("owner waiver, 18 Oct 2026: ONNX scores differed from PyTorch by up to 2.95e-3 with identical kept "
                 "detections, classes and boxes; the score tolerance is reported, not enforced")
# The published model on Kaggle Models; each edition attaches its own variation, so the notebook and the model
# link to each other. Kaggle stays at model version 3.
KAGGLE_MODEL = "rice-pest-detector"
KAGGLE_MODEL_VERSION = 3
# Kaggle tags for the three editions: the names Kaggle accepted on 21 Oct 2026 (it drops any other name).
KAGGLE_KEYWORDS = ["agriculture", "deep-learning", "object-detection"]
KAGGLE_VARIANTS = {
    "r50v5-kaggle": {"source": "r50v5", "manifest": "rice-pest-r50-v5.manifest.json", "label": "r50-v5",
                     "architecture": "RT-DETR with a ResNet-50 backbone",
                     "slug": "rice-pest-detector-train-rt-detr-r50", "title": "Rice pest detector: train RT-DETR r50",
                     "colab_time": "6.2 h on a Colab T4 (22,268 s; run r50-v5, 17 Oct 2026)", "quota_hours": "7",
                     "recorded_date": "17 Oct 2026", "score_tolerance_enforced": True, "public": True,
                     "kaggle_model": "r50-v5"},
    "rfdetr-m-kaggle": {"source": "rfdetr-m", "manifest": "rice-pest-rfdetr-m.manifest.json", "label": "RF-DETR-M",
                        "architecture": "RF-DETR, medium size", "slug": "rice-pest-detector-train-rf-detr-m",
                        "title": "Rice pest detector: train RF-DETR-M",
                        "colab_time": "5.9 h on a Colab T4 (21,108 s; run RF-DETR-M, 17 Oct 2026)",
                        "quota_hours": "6.5", "recorded_date": "17 Oct 2026", "score_tolerance_enforced": True,
                        "public": True, "kaggle_model": "rf-detr-m"},
    "dfine-l-kaggle": {"source": "dfine-l", "manifest": "rice-pest-dfine-l.manifest.json", "label": "D-FINE-L",
                       "architecture": "D-FINE, large size", "slug": "rice-pest-detector-train-d-fine-l",
                       "title": "Rice pest detector: train D-FINE-L",
                       "colab_time": ("about 7.7 h on a Colab T4 (estimated: the resumed part of run D-FINE-L took "
                                      "25,617 s for epochs 3 to 39, 17 Oct 2026)"), "quota_hours": "8.5",
                       "recorded_date": "17 Oct 2026", "score_tolerance_enforced": False, "public": True,
                       "kaggle_model": "d-fine-l"},
}
for _name, _k in KAGGLE_VARIANTS.items():
    _src = VARIANTS[_k["source"]]
    VARIANTS[_name] = {**_k, "platform": "kaggle", "model": _src["model"], "revision": _src["revision"],
                       "run": _src["run"], "input_size": _src.get("input_size", 640),
                       "file": f"train_kaggle_{_k['source']}.ipynb"}


def build(out: Path, revision: str | None = None, variant: str = "r18") -> Path:
    v = VARIANTS[variant]
    revision = revision or v["revision"]
    if v.get("platform") == "kaggle":
        return build_kaggle(Path(out), variant, revision)
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


def slugify(title: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")


def _text_bytes(path: Path) -> bytes:
    """A text file as the notebook embeds it: read with universal newlines, so the bytes match on any checkout."""
    return path.read_text(encoding="utf-8").encode("utf-8")


def _git_blob(data: bytes) -> str:
    return hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest()


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def kaggle_edition(variant: str, revision: str | None = None) -> dict:
    """Settings the notebook's `paths` cell writes to edition.json (read by tools/kaggle_driver.py)."""
    v = VARIANTS[variant]
    manifest = json.loads((ROOT / "models" / v["manifest"]).read_text(encoding="utf-8"))
    if manifest["input_size"] != v["input_size"]:
        raise ValueError(f"{variant}: manifest input size {manifest['input_size']} != recipe {v['input_size']}")
    return {"variant": variant, "model_id": manifest["id"], "base_model": v["model"],
            "revision": revision or v["revision"], "input_size": manifest["input_size"],
            "threshold": manifest["threshold"], "review_below": manifest["review_below"], "epochs": 40,
            "batch_size": 4, "score_tolerance_enforced": v["score_tolerance_enforced"],
            "score_waiver": None if v["score_tolerance_enforced"] else D_FINE_WAIVER}


def carried_files() -> list[tuple[str, Path, bool]]:
    """(path under the work folder, repository file, is text) for everything a Kaggle edition carries."""
    files = [(f"rice_pest_detector/{m.name}", m, True)
             for m in sorted((ROOT / "src" / "rice_pest_detector").glob("*.py"))]
    files += [("rpd_tools/export_onnx.py", ROOT / "tools" / "export_onnx.py", True),
              ("kaggle_driver.py", ROOT / "tools" / "kaggle_driver.py", True),
              ("requirements-kaggle.lock.txt", LOCK_PATH, True)]
    files += [(f"data/{d.name}", d, False) for d in sorted((ROOT / "data").glob("*.json"))]
    return files


# Kaggle rejects a notebook source over 1 MB, so the Kaggle editions download the split and label files from the
# public repository at this commit instead of embedding them (Colab notebooks still embed them). Every file is
# checked for size and SHA-256 here and again by the `carried` cell.
DATA_COMMIT = "ea10632e6eea1e24665f40c36cfb5f38e45e10a3"
DATA_URL = "https://raw.githubusercontent.com/kurtvalcorza/rice-pest-detector/{commit}/data/{name}"


def _data_fetch_cell(paths: list[Path], work: str):
    files = {p.name: (p.stat().st_size, _sha(p.read_bytes())) for p in paths}
    rows = "\n".join(f"    {name!r}: ({size}, {digest!r})," for name, (size, digest) in files.items())
    source = f"""\
# The split and label files, downloaded from the public repository at a fixed commit and checked before use.
import hashlib, pathlib, time, urllib.request
DATA_COMMIT = {DATA_COMMIT!r}
DATA_FILES = {{
{rows}
}}
for name, (size, digest) in DATA_FILES.items():
    url = {DATA_URL!r}.format(commit=DATA_COMMIT, name=name)
    for attempt in range(4):
        try:
            with urllib.request.urlopen(url, timeout=120) as r:
                body = r.read()
            break
        except OSError as err:
            if attempt == 3:
                raise SystemExit(f'Could not download {{name}} ({{err}}). Check that internet is on in the notebook settings.')
            time.sleep(5 * (attempt + 1))
    if len(body) != size or hashlib.sha256(body).hexdigest() != digest:
        raise SystemExit(f'{{name}}: size or SHA-256 differs from the pinned file; refusing to train on it.')
    pathlib.Path('{work}/data', name).write_bytes(body)
    print(f'{{name}}: {{size:,}} bytes, SHA-256 ok')"""
    return _cell(new_code_cell, "data", source)


def _kaggle_cells(variant: str, revision: str) -> list:
    if str(ROOT) not in sys.path:  # run as a script: make the `tools` package importable
        sys.path.insert(0, str(ROOT))
    from tools import kaggle_cells as kc

    v = VARIANTS[variant]
    edition = kaggle_edition(variant, revision)
    manifest = json.loads((ROOT / "models" / v["manifest"]).read_text(encoding="utf-8"))
    ed = {**v, **edition, "revision": revision,
          "model_url": f"https://www.kaggle.com/models/{KAGGLE_OWNER}/{KAGGLE_MODEL}/onnx/{v['kaggle_model']}",
          "recorded_map50": f"{manifest['validation']['species_map50']:.3f}",
          "recorded_count": f"{manifest['validation']['count_accuracy']:.3f}",
          "resize_note": ("the model reads them at 640 × 640." if edition["input_size"] == 640 else
                          f"{v['label']} resizes them to {edition['input_size']} × {edition['input_size']}, its "
                          "native input size.")}
    md, code = new_markdown_cell, new_code_cell
    cells = [_cell(md, "intro", kc.intro(ed)), _cell(md, "problem", kc.problem(ed, DATA_CREDIT)),
             _cell(code, "runtime", kc.RUNTIME_SOURCE),
             _cell(code, "paths", kc.paths(ed, pprint.pformat(edition, sort_dicts=False, width=100)))]
    carried, modules, data_paths = {}, 0, []
    for target, path, is_text in carried_files():
        if not is_text:
            data_paths.append(path)
            carried[target] = _sha(path.read_bytes())
            continue
        if target.endswith(".txt"):
            cell_id = "lock"
        else:
            cell_id, modules = f"module-{modules:02d}", modules + 1
        cells.append(_cell(code, cell_id, f"%%writefile {kc.WORK}/{target}\n" + path.read_text(encoding="utf-8")))
        carried[target] = _sha(_text_bytes(path))
    cells.append(_data_fetch_cell(data_paths, kc.WORK))
    cells += [
        _cell(code, "carried", kc.carried(carried)),
        _cell(code, "carrier", kc.CARRIER_SOURCE),
        _cell(code, "env-log", kc.ENV_LOG_SOURCE),
        _cell(code, "fetch", kc.FETCH_SOURCE),
        _cell(code, "validate", kc.VALIDATE_SOURCE),
        _cell(code, "resume", kc.RESUME_SOURCE),
        _cell(md, "fit-text", kc.fit_text(ed)),
        _cell(code, "fit", kc.FIT_SOURCE),
        _cell(code, "evaluate", kc.EVALUATE_SOURCE),
        _cell(code, "export", kc.EXPORT_SOURCE),
        _cell(code, "reload", kc.RELOAD_SOURCE),
        _cell(code, "inference", kc.INFERENCE_SOURCE),
        _cell(code, "test-look", kc.TEST_LOOK_SOURCE),
        _cell(code, "summary", kc.SUMMARY_SOURCE),
        _cell(md, "interpret", kc.interpret(ed)),
        _cell(md, "did-not-work", kc.DID_NOT_WORK),
        _cell(md, "references", kc.REFERENCES),
    ]
    return cells


def kernel_metadata(variant: str) -> dict:
    v = VARIANTS[variant]
    return {"id": f"{KAGGLE_OWNER}/{v['slug']}", "title": v["title"], "code_file": v["file"], "language": "python",
            "kernel_type": "notebook", "is_private": not v["public"], "enable_gpu": True, "enable_tpu": False,
            "enable_internet": True, "dataset_sources": [], "competition_sources": [], "kernel_sources": [],
            "model_sources": [f"{KAGGLE_OWNER}/{KAGGLE_MODEL}/onnx/{v['kaggle_model']}/{KAGGLE_MODEL_VERSION}"],
            "keywords": KAGGLE_KEYWORDS}


def cell_sources_sha256(nb: dict) -> str:
    """SHA-256 of the cell sources joined with "\\n\\0" in order (Kaggle rewrites notebook metadata, not sources)."""
    sources = ["".join(c["source"]) if isinstance(c["source"], list) else c["source"] for c in nb["cells"]]
    return _sha("\n\0".join(sources).encode("utf-8"))


def declaration(variant: str, revision: str, notebook: Path) -> dict:
    v = VARIANTS[variant]
    edition = kaggle_edition(variant, revision)
    meta = kernel_metadata(variant)
    data = notebook.read_bytes()
    embedded = {path.relative_to(ROOT).as_posix(): _sha(_text_bytes(path) if is_text else path.read_bytes())
                for _, path, is_text in carried_files()}
    return {
        "variant": variant,
        "notebook_sha256": _sha(data),
        "cell_sources_sha256": cell_sources_sha256(json.loads(data)),
        "embedded": embedded,
        "lock": {"path": LOCK_PATH.relative_to(ROOT).as_posix(), "sha256": _sha(_text_bytes(LOCK_PATH)),
                 "uv": "0.12.15", "python": "3.12.12", "platform": "x86_64-manylinux_2_28"},
        "generator": {f"tools/{n}": _git_blob(_text_bytes(ROOT / "tools" / n))
                      for n in ("build_notebook.py", "kaggle_cells.py")},
        "model": {"base_model": v["model"], "revision": revision, "manifest": f"models/{v['manifest']}",
                  "threshold": edition["threshold"], "input_size": edition["input_size"]},
        "kaggle": {"id": meta["id"], "is_private": meta["is_private"], "accelerator": "NvidiaTeslaT4",
                   "enable_internet": True},
    }


def _write_json(path: Path, obj) -> None:
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(json.dumps(obj, indent=1, ensure_ascii=False) + "\n")


def build_kaggle(out: Path, variant: str, revision: str) -> Path:
    """Write the notebook to `out`, and kernel-metadata.json and declaration.json beside it."""
    v = VARIANTS[variant]
    if len(v["title"]) >= 40 or slugify(v["title"]) != v["slug"]:
        raise ValueError(f"{variant}: the Kaggle title must be under 40 characters and slugify to its id")
    nb = new_notebook(cells=_kaggle_cells(variant, revision), metadata={
        # Kaggle runs notebooks with papermill, which stops at once without a kernel name.
        "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
        "accelerator": "GPU",
        "kaggle": {"accelerator": "nvidiaTeslaT4", "isInternetEnabled": True, "language": "python"},
        "notebook_standard": {"spec": "NOTEBOOK_SPEC 2.5", "profile": "E2E", "mode": "REFERENCE", "kind": "TUTORIAL"},
    })
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", encoding="utf-8", newline="\n") as fh:
        nbformat.write(nb, fh)
    _write_json(out.parent / "kernel-metadata.json", kernel_metadata(variant))
    _write_json(out.parent / "declaration.json", declaration(variant, revision, out))
    return out


def committed_path(variant: str) -> Path:
    v = VARIANTS[variant]
    if v.get("platform") == "kaggle":
        return KAGGLE_DIR / v["slug"] / v["file"]
    return ROOT / "notebooks" / ("train_colab.ipynb" if variant == "r18" else f"train_colab_{variant}.ipynb")


def check(variant: str, revision: str | None = None) -> list[str]:
    """Rebuild one variant in a temporary folder; return the committed files that differ (empty: all equal)."""
    target = committed_path(variant)
    names = [target.name]
    if VARIANTS[variant].get("platform") == "kaggle":
        names += ["kernel-metadata.json", "declaration.json"]
    with tempfile.TemporaryDirectory() as tmp:
        fresh = build(Path(tmp) / target.name, revision, variant)
        return [n for n in names if not (target.parent / n).is_file()
                or (fresh.parent / n).read_bytes() != (target.parent / n).read_bytes()]


def check_all() -> int:
    variants = [*COLAB_VARIANTS, *KAGGLE_VARIANTS]
    failed = 0
    for variant in variants:
        diff = check(variant)
        failed += bool(diff)
        status = "OK  " if not diff else "DIFF"
        target = committed_path(variant)
        shown = target.relative_to(ROOT).as_posix() if target.is_relative_to(ROOT) else str(target)
        print(f"{status} {variant}: {shown}"
              + (f" ({', '.join(diff)})" if diff else ""))
    print(f"{len(variants) - failed} of {len(variants)} notebooks match a fresh build")
    return 1 if failed else 0


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--revision", help="base-model revision (default: the variant's own)")
    parser.add_argument("--variant", choices=sorted(VARIANTS), default="r18")
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--check-all", action="store_true", help="check every committed notebook; exit 1 on any difference")
    args = parser.parse_args()
    if args.check_all:
        sys.exit(check_all())
    if args.check:
        sys.exit(1 if check(args.variant, args.revision) else 0)
    print(build(committed_path(args.variant), args.revision, args.variant))


if __name__ == "__main__":
    main()
