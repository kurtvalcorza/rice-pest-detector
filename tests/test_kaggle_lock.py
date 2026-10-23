"""The Kaggle editions' hash lock: format, pins and an import-map audit (spec 010, FR-028, FR-030)."""

import ast
import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
KAGGLE = ROOT / "notebooks" / "kaggle"
LOCK = KAGGLE / "requirements-kaggle.lock.txt"
PINS = {"torch": "2.14.1", "transformers": "5.20.1", "numpy": "2.5.4", "pillow": "13.0.0", "pycocotools": "2.0.11",
        "scipy": "1.18.1", "onnx": "1.23.2", "onnxruntime": "1.31.0"}
# import name -> distribution name, where they differ
DIST_OF = {"PIL": "pillow", "yaml": "pyyaml", "google": "protobuf"}
# lazy backends of the used transformers classes and the matcher (research R3, ENV13)
LAZY = ("scipy", "pycocotools", "safetensors", "huggingface-hub", "pillow", "onnx", "onnxruntime")
# transformers backend names -> distribution; None = optional, not needed by these notebooks (reason given)
BACKENDS = {"torch": "torch", "scipy": "scipy", "vision": "pillow", "accelerate": None}
OPTIONAL_REASON = {"accelerate": "only for multi-process loss reduction; one GPU and one process are used"}


def _locked() -> dict[str, str]:
    text = LOCK.read_text(encoding="utf-8")
    return {m.group(1).lower(): m.group(2) for m in re.finditer(r"^([A-Za-z0-9_.-]+)==(\S+)", text, re.MULTILINE)}


def _norm(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def test_lock_and_inputs_exist_with_hashes_and_header():
    assert (KAGGLE / "requirements-kaggle.in").is_file() and LOCK.is_file()
    text = LOCK.read_text(encoding="utf-8")
    header = text.splitlines()[1]
    for flag in ("--python-version 3.12", "--python-platform x86_64-manylinux_2_28", "--generate-hashes",
                 "--only-binary :all:"):
        assert flag in header
    blocks = re.split(r"\n(?=[A-Za-z0-9_.-]+==)", text)
    reqs = [b for b in blocks if re.match(r"[A-Za-z0-9_.-]+==", b)]
    assert len(reqs) == len(_locked()) > 0
    assert all("--hash=sha256:" in b for b in reqs)
    assert "\r" not in LOCK.read_bytes().decode("utf-8")


def test_principal_pins():
    locked = _locked()
    for name, version in PINS.items():
        assert locked.get(name) == version, name
    inputs = (KAGGLE / "requirements-kaggle.in").read_text(encoding="utf-8")
    for name, version in PINS.items():
        assert f"{name}=={version}" in inputs


def _imports(path: Path) -> set[str]:
    names = set()
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Import):
            names |= {a.name.split(".")[0] for a in node.names}
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            names.add(node.module.split(".")[0])
    return names


def test_import_map_audit_every_runtime_import_is_locked_or_stdlib():
    locked = {_norm(n) for n in _locked()}
    files = [*sorted((ROOT / "src" / "rice_pest_detector").glob("*.py")), ROOT / "tools" / "export_onnx.py",
             ROOT / "tools" / "kaggle_driver.py"]
    own = {"rice_pest_detector", "rpd_tools", "tools"}
    missing = {}
    for f in files:
        for name in _imports(f) - own - set(sys.stdlib_module_names):
            if _norm(DIST_OF.get(name, name)) not in locked:
                missing.setdefault(name, []).append(f.name)
    assert missing == {}
    for dist in LAZY:
        assert _norm(dist) in locked, dist


def test_transformers_backend_checks_for_the_three_architectures_are_covered():
    transformers = pytest.importorskip("transformers")
    if transformers.__version__ != PINS["transformers"]:
        pytest.skip(f"installed transformers {transformers.__version__} is not the pinned {PINS['transformers']}")
    base = Path(transformers.__file__).parent
    files = [*(base / "models" / m / f for m in ("rt_detr", "d_fine", "rf_detr")
               for f in sorted(p.name for p in (base / "models" / m).glob("*.py"))),
             *(base / "loss" / f"loss_{m}.py" for m in ("rt_detr", "d_fine", "rf_detr", "for_object_detection"))]
    found = set()
    for f in files:
        if not f.is_file():
            continue
        text = f.read_text(encoding="utf-8")
        found |= set(re.findall(r"is_([a-z0-9_]+?)_available", text))
        for group in re.findall(r"requires_backends\([^,]+,\s*\[([^\]]*)\]", text):
            found |= set(re.findall(r"[\"']([a-z0-9_]+)[\"']", group))
    print("transformers backend checks found:", sorted(found))
    assert found, "audit found no backend checks: the scan is broken"
    assert found <= set(BACKENDS), sorted(found - set(BACKENDS))
    locked = {_norm(n) for n in _locked()}
    for backend in found:
        dist = BACKENDS[backend]
        assert dist is None and backend in OPTIONAL_REASON or _norm(dist) in locked, backend
