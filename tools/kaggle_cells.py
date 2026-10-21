"""Cell sources for the Kaggle editions of the training notebook (used by tools/build_notebook.py).

Everything here is published. The kernel side of each notebook uses the standard library only; every stage that
needs PyTorch, transformers, NumPy or Pillow runs in the notebook's own environment through `run_stage`, which
starts `kaggle_driver.py` (tools/kaggle_driver.py) as a child process.
"""

UV_URL = ("https://files.pythonhosted.org/packages/1e/fd/432451d732917c49152a291de3ef171aa6b0f1a22d39780fb2c1f085ca4c/"
          "uv-0.12.15-py3-none-manylinux_2_17_x86_64.manylinux2014_x86_64.whl")
UV_SHA256 = "aee9802f46bae436bd91751bb33ddeb379ef1596b5c19df193219d545d244b60"
UV_BYTES = 20_081_404
UV_VERSION = "0.12.15"
ENV_PYTHON = "3.12.12"
LOCK_PLATFORM = "x86_64-manylinux_2_28"
WORK = "/tmp/rpd"
TEST_LOOKS_SPENT = "Test split: skipped (default). Both looks the rules allow were spent on 13 and 18 Oct 2026."

USE_NOTICE = (
    "> **Use notice.** For research, training and evaluation only. The model is a teaching demo: it has not been "
    "validated in the field or by experts, and it is not a pest-surveillance or pest-alert system. Its counts are "
    "experimental estimates, not agronomic advice, and must not be the basis for any pest-management decision. "
    "Running this notebook downloads third-party model weights and a dataset under their own licences and uses "
    "your own Kaggle GPU quota. Results here are tutorial evidence, not benchmarks. Everything is provided \"as "
    "is\", without warranty of any kind."
)


def intro(ed: dict) -> str:
    return f"""# Rice pest detector: train {ed['label']} on Kaggle

**End-to-end reference notebook (E2E, REFERENCE). It runs the full published recipe and is not a release-grade \
tutorial under the owner's notebook standard.**

{USE_NOTICE}

This notebook retrains the {ed['label']} detector ({ed['architecture']}) of the open-source rice pest detector \
project with the recipe that produced its published model. It counts two rice pests, the rice black bug (RBB) and \
the white stemborer (WSB), in light-trap photos, as a teaching example. Choose **Run all**; no cell needs editing.

**What it does**

1. Checks the runtime (Linux x86_64, one T4 GPU, Internet on) before anything else.
2. Builds its own Python {ENV_PYTHON} environment from a hash-locked package list, without touching Kaggle's \
preinstalled packages.
3. Downloads the dataset archive from Zenodo and checks it by size, MD5 and SHA-256, and every image by SHA-256.
4. Validates the data: split sizes, file names, class ids, image sizes and the most crowded tray.
5. Fine-tunes `{ed['base_model']}` for {ed['epochs']} epochs and keeps the checkpoint with the best validation \
species mAP50.
6. Evaluates that checkpoint on the validation photos at the published counting threshold ({ed['threshold']}).
7. Exports it to ONNX, reloads the file in a fresh process and checks it against the trained model.
8. Counts insects on sample validation photos with the reloaded ONNX model and writes a run summary.

**What it needs**

- A Kaggle account that is phone-verified (Kaggle requires this for GPU and Internet).
- Settings: **Accelerator: GPU T4 x2** (one T4 is used) and **Internet on**.
- Time: the full {ed['epochs']}-epoch recipe, measured at {ed['colab_time']}, plus a few minutes to build the \
environment and about 20 minutes to download and check the images. Times on Kaggle are not yet measured.
- Kaggle ends a session after 12 hours. If the session ends early, the run is lost and starts again from the \
beginning, unless you attach an earlier run's output and set `RESUME_FROM`.
- The run uses about {ed['quota_hours']} hours of your weekly Kaggle GPU quota.

This is a reference notebook: it reproduces the published recipe in full instead of a short tutorial run.

**The published model.** The model this recipe produced is on Kaggle Models as [{ed['label']}]({ed['model_url']}). This notebook attaches it as an input, so the model page lists the notebook that trains it; the notebook does not load it. The run's own model is new and will not match the published file byte for byte.
"""


def problem(ed: dict, credit: str) -> str:
    return f"""## Problem and data

**Problem.** Light traps catch many insects overnight; counting the two pests in a photo of the tray by hand is \
slow. This notebook trains a detector that finds each rice black bug and white stemborer (female and male of each, \
four classes) and counts them per species. It is a teaching example of fine-tuning and checking a detector.

**Scope.** The model is a teaching demo. It is not for farmers, it has not been validated in the field, and \
nothing here is advice on what to do about pests.

**Data.** The photos and labels come from an open dataset by its authors (Deleña et al.), published on Zenodo \
under CC BY 4.0. The notebook downloads the archive at run time; no image is redistributed with it or saved in its \
output.

{credit}

**Label lineage.** The original YOLO labels were converted to COCO JSON; 652 label files held polygon rows, each \
converted to its bounding box; one image family was excluded because an image had no label file. Images were \
grouped into families (an original and its augmented variants), near-duplicate families were merged and the \
families were re-split 70 / 15 / 15 at random by family with a fixed seed (20261013), on the assumption that \
families are independent. The images are pre-stretched to 640 × 640 in the archive; {ed['resize_note']}

**Why the notebook is about 4.5 MB.** The labels and the split manifest (about 4.4 MB of JSON, compressed in the \
data cells below) travel inside the notebook so that it needs no repository clone; the images do not, so that none \
is redistributed. Preprocessing is fixed (resize and division by 255), so nothing is fitted on any split.
"""


RUNTIME_SOURCE = """\
import json, os, platform, shutil, subprocess, time, urllib.error, urllib.request
SESSION_START = time.time()
print('Supported runtime: a Kaggle notebook on Linux x86_64 with the GPU T4 accelerator and Internet on.')
if platform.system() != 'Linux' or platform.machine() != 'x86_64':
    raise RuntimeError(f'Unsupported platform {platform.system()} {platform.machine()}: the package lock is built for '
                       'Linux x86_64 only. Run this notebook on Kaggle with the GPU T4 accelerator.')
try:
    _gpu = subprocess.run(['nvidia-smi', '--query-gpu=name', '--format=csv,noheader'],
                          capture_output=True, text=True, timeout=60)
    GPUS = [n.strip() for n in _gpu.stdout.splitlines() if n.strip()] if _gpu.returncode == 0 else []
except (FileNotFoundError, subprocess.TimeoutExpired):
    GPUS = []
if not GPUS:
    raise RuntimeError('No GPU found. In the editor open Settings > Accelerator, choose GPU T4 x2, then Run all.')
if 'T4' not in GPUS[0]:
    raise RuntimeError(f'The GPU is {GPUS[0]}, not a T4. In Settings > Accelerator choose GPU T4 x2, then Run all.')
print('GPU:', ', '.join(GPUS), '(device 0 is used)')
try:
    urllib.request.urlopen(urllib.request.Request('https://zenodo.org/api/records/20066074', method='HEAD'),
                           timeout=30).close()
except urllib.error.HTTPError:
    pass  # an HTTP answer means the network is up
except (urllib.error.URLError, TimeoutError, OSError) as exc:
    raise RuntimeError('zenodo.org cannot be reached: Internet is off. In Settings turn Internet on (this needs a '
                       'phone-verified Kaggle account), then Run all.') from exc
print('Internet: zenodo.org reachable')
for _folder in ('/tmp', '/kaggle/working'):
    print(f'free space in {_folder}: {shutil.disk_usage(_folder).free / 1e9:.1f} GB')"""


def paths(ed: dict, edition_literal: str) -> str:
    return f"""\
import json, os
from pathlib import Path
WORK = '{WORK}'  # scratch: package, labels, archive, images and environment; not saved
RUN_DIR = '/kaggle/working/{ed['run']}'  # saved output
RESUME_FROM = ''  # @param {{type:"string"}}
EDITION = {edition_literal}
for _sub in ('rice_pest_detector', 'rpd_tools', 'data', 'images'):
    os.makedirs(os.path.join(WORK, _sub), exist_ok=True)
os.makedirs(RUN_DIR, exist_ok=True)
Path(WORK, 'edition.json').write_text(json.dumps(EDITION, indent=1))
print('scratch:', WORK, '| output:', RUN_DIR)
print(json.dumps(EDITION, indent=1))"""


def carried(table: dict) -> str:
    rows = "\n".join(f"    {name!r}: {digest!r}," for name, digest in table.items())
    return f"""\
import hashlib
from pathlib import Path
CARRIED = {{
{rows}
}}
for _name, _expected in CARRIED.items():
    _path = Path(WORK, _name)
    if not _path.is_file() or hashlib.sha256(_path.read_bytes()).hexdigest() != _expected:
        raise RuntimeError(f'{{_name}}: the file written above differs from the build (SHA-256). Run all again.')
print(len(CARRIED), 'carried files match the build (SHA-256), the package lock included')"""


# Defined in the kernel by the carrier cell; tests execute this string with their own PYTHON, ENV, WORK, RUN_DIR.
RUN_STAGE_SOURCE = """\
def _record_time(stage, seconds):
    path = Path(RUN_DIR, 'stage_times.json')
    times = json.loads(path.read_text()) if path.exists() else {}
    times[stage] = round(seconds, 1)
    path.write_text(json.dumps(times, indent=1))


def run_stage(stage, *options):
    log = Path(RUN_DIR, f'{stage}.log')
    cmd = [PYTHON, '-u', str(Path(WORK, 'kaggle_driver.py')), '--stage', stage, '--work', WORK,
           '--run-dir', RUN_DIR, *options]
    print('Running stage', stage, 'in the notebook environment; log:', log, flush=True)
    started = time.time()
    with log.open('w', encoding='utf-8') as output:
        child = subprocess.Popen(cmd, env=ENV, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        for line in child.stdout:
            output.write(line)
            output.flush()
            print(line.rstrip(), flush=True)
        child.wait()
    _record_time(stage, time.time() - started)
    if child.returncode:
        print(log.read_text(encoding='utf-8')[-6000:])
        raise RuntimeError(f'Stage {stage!r} failed (exit {child.returncode}); the end of its log is repeated above.')"""

CARRIER_SOURCE = f"""\
import hashlib, io, json, os, shutil, subprocess, time, urllib.error, urllib.request, zipfile
from pathlib import Path
UV_URL = '{UV_URL}'
UV_SHA256 = '{UV_SHA256}'
UV_BYTES = {UV_BYTES}
LOCK = Path(WORK, 'requirements-kaggle.lock.txt')
_started = time.time()
for _attempt in range(3):
    try:
        with urllib.request.urlopen(UV_URL, timeout=90) as _response:
            _wheel = _response.read(UV_BYTES + 1)
        break
    except (urllib.error.URLError, TimeoutError, ConnectionError) as _exc:
        if _attempt == 2:
            raise RuntimeError('Could not download uv {UV_VERSION}; check that Internet is on, then Run all.') from _exc
        time.sleep(2 ** _attempt)
if len(_wheel) != UV_BYTES or hashlib.sha256(_wheel).hexdigest() != UV_SHA256:
    raise RuntimeError('The uv {UV_VERSION} wheel does not match its pinned size and SHA-256: refusing to use it.')
with zipfile.ZipFile(io.BytesIO(_wheel)) as _archive:
    _member = next(n for n in _archive.namelist() if n.endswith('.data/scripts/uv'))
    UV = Path(WORK, 'uv')
    UV.write_bytes(_archive.read(_member))
UV.chmod(0o700)
ENV = dict(os.environ, HF_HUB_DISABLE_TELEMETRY='1', HF_HUB_DISABLE_IMPLICIT_TOKEN='1', DO_NOT_TRACK='1')
for _key in ('HF_TOKEN', 'HUGGING_FACE_HUB_TOKEN', 'PYTHONPATH', 'PYTHONHOME', 'PYTHONSTARTUP'):
    ENV.pop(_key, None)


def _step(name, cmd):
    done = subprocess.run(cmd, env=ENV)
    if done.returncode:
        raise RuntimeError(f'Environment step failed: {{name}} (exit {{done.returncode}}). Nothing was trained; '
                           'read the messages above, then Run all again.')


shutil.rmtree(Path(WORK, 'env'), ignore_errors=True)
_step('create the Python {ENV_PYTHON} environment',
      [str(UV), 'venv', '--managed-python', '--python', '{ENV_PYTHON}', str(Path(WORK, 'env'))])
PYTHON = str(Path(WORK, 'env', 'bin', 'python'))
_step('install the hash-locked packages',
      [str(UV), 'pip', 'install', '--python', PYTHON, '--require-hashes', '--only-binary', ':all:',
       '--index-url', 'https://pypi.org/simple', '-r', str(LOCK)])
VERSION_CHECK = ('import sys, numpy, PIL, onnxruntime, torch, transformers; '
                 'print("Python", sys.version.split()[0]); print("torch", torch.__version__, "CUDA", torch.version.cuda); '
                 'print("transformers", transformers.__version__); print("numpy", numpy.__version__); '
                 'print("Pillow", PIL.__version__); print("onnxruntime", onnxruntime.__version__); '
                 'assert torch.cuda.is_available(), "CUDA is not visible inside the notebook environment"; '
                 'print("GPU", torch.cuda.get_device_name(0))')
_step('check versions and CUDA inside the environment', [PYTHON, '-c', VERSION_CHECK])

{RUN_STAGE_SOURCE}


_record_time('environment', time.time() - _started)
print(f'environment ready in {{time.time() - _started:.0f}} s; Kaggle\\'s own packages were not changed')"""

ENV_LOG_SOURCE = "run_stage('env-log')"
FETCH_SOURCE = "run_stage('fetch')"
VALIDATE_SOURCE = "run_stage('validate')"
RESUME_SOURCE = "run_stage('resume', RESUME_FROM)"
FIT_SOURCE = "run_stage('fit')"
EVALUATE_SOURCE = """\
run_stage('evaluate')
_val = json.loads(Path(RUN_DIR, 'val_metrics.json').read_text())['headline']
print('\\n| metric | value |\\n| :-- | --: |')
for _k in ('map50_species', 'map50_four_class', 'count_accuracy', 'count_accuracy_no_detection_baseline', 'wsb30_mae'):
    print(f'| {_k} | {_val[_k]} |')"""
EXPORT_SOURCE = "run_stage('export')"
RELOAD_SOURCE = "run_stage('reload')"
INFERENCE_SOURCE = "run_stage('inference')"
TEST_LOOK_SOURCE = f"""\
RUN_TEST_LOOK = False  # @param {{type:"boolean"}}
if RUN_TEST_LOOK:
    run_stage('test-look')
else:
    print('{TEST_LOOKS_SPENT}')"""
SUMMARY_SOURCE = """\
run_stage('summary')
print('machine-readable summary:', Path(RUN_DIR, 'run_summary.json'))
print(f'whole notebook: {(time.time() - SESSION_START) / 3600:.2f} h')"""


def fit_text(ed: dict) -> str:
    return f"""## Training method and settings

- **Method:** full fine-tune of `{ed['base_model']}` (revision `{ed['revision']}`); every parameter is trainable.
- **Optimiser:** AdamW, learning rate 1e-4 (backbone 1e-5), weight decay 1e-4, gradient clipping 0.1; cosine \
schedule over {ed['epochs']} epochs.
- **Batch and precision:** batch {ed['batch_size']}; fp16 autocast, with the Hungarian matcher and the losses in \
float32.
- **Input:** {ed['input_size']} × {ed['input_size']} pixels; 300 queries.
- **Seeds:** training seed 20261013 and a per-epoch data-loader seed.
- **Checkpoint selection:** after each epoch the model is evaluated on the validation split; `best.pt` keeps the \
epoch with the highest validation species mAP50. The validation photos are never used for gradient updates, only \
to choose the checkpoint.

These are the published recipe's values, not tutorial values: the run takes hours (see the top of the notebook). \
Training loss is not task quality; quality is judged on validation mAP50 and counts. `last.pt` keeps the optimiser \
state so that a run can be resumed from an attached earlier output."""


def interpret(ed: dict) -> str:
    return f"""## How to read the results

- **These are this run's numbers.** The evaluation above is one validation pass at the published threshold \
({ed['threshold']}): tutorial evidence, not a benchmark. Read your own printed numbers and `run_summary.json`.
- **They will differ slightly from the recorded run.** GPU training is not bit-repeatable, and Kaggle's GPU driver \
and CUDA libraries differ from the Colab run that produced the published model; NumPy and Pillow are pinned to the \
versions the project used. For {ed['label']} the project recorded validation species mAP50 {ed['recorded_map50']} \
(run {ed['label']}, Colab T4, {ed['recorded_date']}).
- **Count accuracy here is not the recorded figure.** The recorded count accuracy ({ed['recorded_count']}) is \
out-of-fold: the threshold was re-chosen on each fold. This notebook counts once at the published threshold, so \
the two are different estimates.
- **What the evaluation does not show.** It uses validation photos from the same dataset and traps; it says nothing \
about other traps, cameras or regions. The base models were pretrained on COCO (and RF-DETR's backbone on a large \
image collection), which cannot be shown to exclude similar images. Scores are raw sigmoid outputs, not calibrated \
probabilities; the review flag (`review_below` = {ed['review_below']}) was set by offline calibration on validation.
- **Counting rule.** A detection is counted when its score is at least the published threshold."""


DID_NOT_WORK = """## What did not work

- **An older transformers release trained the wrong loss.** The first two runs (r18-1 and r50-1) used transformers \
4.57.6, whose RT-DETR main loss was computed over the denoising queries as well. transformers 5.18 fixed it; the \
published models were retrained on 5.20.1, and the older runs are kept as history only (evaluation record, wave 2).
- **Early peaks, then a slow drift.** All three models reach their best validation species mAP50 within the first \
four epochs and then drift down slowly (r50-v5 0.908 and RF-DETR-M 0.891 at the last epoch; evaluation record, \
wave 2). The checkpoint is chosen on validation, so the drift does not reach the exported model, but the best epoch \
is unstable from run to run.
- **The threshold grid edge.** The pre-registered threshold grid stops at 0.50; one r50-v5 fold and four D-FINE-L \
folds chose 0.50, so their best threshold may lie above the grid. Recorded, not changed: the grid was fixed \
before the results (evaluation record, wave 2 and D-FINE-L).
- **Best on validation, weakest on test.** RF-DETR-M had the best out-of-fold validation count accuracy (0.846) \
but the weakest on the test split (0.806, a post-hoc comparison by owner exception, 18 Oct 2026). Differences of a \
few points between these models are within run-to-run and split-to-split variation.
- **D-FINE-L's ONNX scores.** Its ONNX scores differ from PyTorch by up to 2.95e-3 with identical kept detections, \
classes and boxes, above the 1e-3 tolerance. The owner waived the score tolerance for D-FINE-L on 18 Oct 2026; its \
reload check still enforces kept detections, classes and boxes (evaluation record, D-FINE-L parity).

**Which model the project chose, and why.** r50-v5 is the demo model. It was chosen on validation under rules \
written before any result: it met rule A against r50-1, and neither RF-DETR-M nor D-FINE-L met rule B against it."""

REFERENCES = """## References

1. Deleña, R.; Balleras, G.; Dequiña, B. J.; Jumawan, R.; Flores, C. Annotated light-trap rice pest image dataset \
with detector-derived region-of-interest crops for species-sex recognition of rice black bug and white stemborer. \
Version 1. Zenodo. [doi:10.5281/zenodo.20066074](https://doi.org/10.5281/zenodo.20066074)
2. Y. Zhao et al., "DETRs Beat YOLOs on Real-time Object Detection" (RT-DETR). \
[arXiv:2304.08069](https://arxiv.org/abs/2304.08069)
3. I. Robinson et al., "RF-DETR: Neural Architecture Search for Real-Time Detection Transformers". \
[arXiv:2511.09554](https://arxiv.org/abs/2511.09554)
4. Y. Peng et al., "D-FINE: Redefine Regression Task in DETRs as Fine-grained Distribution Refinement". \
[arXiv:2410.13842](https://arxiv.org/abs/2410.13842)
5. COCO evaluation (pycocotools). [github.com/ppwwyyxx/cocoapi](https://github.com/ppwwyyxx/cocoapi)
6. Rice pest detector, the project repository. \
[github.com/kurtvalcorza/rice-pest-detector](https://github.com/kurtvalcorza/rice-pest-detector)
7. Rice pest detector, the published models on Kaggle. [kaggle.com/models/kurtvalcorza/rice-pest-detector](https://www.kaggle.com/models/kurtvalcorza/rice-pest-detector)"""
