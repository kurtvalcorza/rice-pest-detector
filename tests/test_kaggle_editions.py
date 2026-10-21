"""Kaggle editions (spec 010): cell contract, metadata, declaration, kernel helpers and driver stages."""

import ast
import hashlib
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

import nbformat
import pytest

import tools.build_notebook as bn
from tools import kaggle_cells as kc
from tools import kaggle_driver as kd

ROOT = Path(__file__).resolve().parents[1]
EDITIONS = ("r50v5-kaggle", "rfdetr-m-kaggle", "dfine-l-kaggle")
CELL_ORDER_HEAD = ["intro", "problem", "runtime", "paths"]
CELL_ORDER_TAIL = ["carried", "carrier", "env-log", "fetch", "validate", "resume", "fit-text", "fit", "evaluate",
                   "export", "reload", "inference", "test-look", "summary", "interpret", "did-not-work", "references"]
HEAVY = {"torch", "transformers", "numpy", "PIL"}


@pytest.fixture(scope="module")
def built(tmp_path_factory):
    out = {}
    for variant in EDITIONS:
        folder = tmp_path_factory.mktemp(variant)
        path = bn.build(folder / bn.VARIANTS[variant]["file"], variant=variant)
        out[variant] = (path, nbformat.read(path, as_version=4))
    return out


def _cell(nb, cell_id):
    return next(c.source for c in nb.cells if c.get("id") == cell_id)


def _is_writefile(source: str) -> bool:
    return source.startswith("%%writefile ")


def _markdown(nb) -> str:
    return "\n".join(c.source for c in nb.cells if c.cell_type == "markdown")


def _kernel_code(nb) -> list[str]:
    """Code the kernel itself runs: everything but the files written for the environment and the data blobs."""
    return [c.source for c in nb.cells if c.cell_type == "code" and not _is_writefile(c.source)]


# ------------------------------------------------------------------ structure (T011)


def test_three_kaggle_variants_build_into_their_own_folders(built):
    for variant in EDITIONS:
        v = bn.VARIANTS[variant]
        assert v["platform"] == "kaggle"
        committed = bn.committed_path(variant)
        assert committed == ROOT / "notebooks" / "kaggle" / v["slug"] / f"train_kaggle_{v['source']}.ipynb"
        assert committed.is_file()


def test_no_colab_or_drive_and_credit_present(built):
    for variant, (path, nb) in built.items():
        text = path.read_text(encoding="utf-8")
        for needle in ("google.colab", "drive.mount", "/content/"):
            assert needle not in text, (variant, needle)
        assert "doi.org/10.5281/zenodo.20066074" in _cell(nb, "problem") and "CC BY 4.0" in _cell(nb, "problem")


def test_metadata_declares_reference_notebook_and_kaggle_settings(built):
    for _, nb in built.values():
        assert nb.metadata["notebook_standard"] == {"spec": "NOTEBOOK_SPEC 2.5", "profile": "E2E",
                                                    "mode": "REFERENCE", "kind": "TUTORIAL"}
        assert nb.metadata["kaggle"] == {"accelerator": "nvidiaTeslaT4", "isInternetEnabled": True,
                                         "language": "python"}


def test_every_code_cell_compiles_and_cells_follow_the_contract_order(built):
    for variant, (_, nb) in built.items():
        ids = [c["id"] for c in nb.cells]
        assert ids[:4] == CELL_ORDER_HEAD and ids[-len(CELL_ORDER_TAIL):] == CELL_ORDER_TAIL, variant
        middle = ids[4:-len(CELL_ORDER_TAIL)]
        assert all(re.fullmatch(r"module-\d\d|lock|data", i) for i in middle)
        assert len(set(ids)) == len(ids)
        for c in nb.cells:
            assert not c.get("outputs") and c.get("execution_count") is None
            if c.cell_type != "code":
                continue
            if _is_writefile(c.source):
                target, body = c.source.split("\n", 1)
                if target.endswith(".py"):
                    compile(body, target, "exec")
            else:
                compile(c.source, c["id"], "exec")


def test_editions_are_deterministic(built, tmp_path):
    path, _ = built["r50v5-kaggle"]
    again = bn.build(tmp_path / path.name, variant="r50v5-kaggle")
    for name in (path.name, "kernel-metadata.json", "declaration.json"):
        assert (again.parent / name).read_bytes() == (path.parent / name).read_bytes()


# ------------------------------------------------------------------ kernel-metadata.json and declaration (T013)


def test_kernel_metadata_follows_the_contract(built):
    for variant, (path, _) in built.items():
        v = bn.VARIANTS[variant]
        meta = json.loads((path.parent / "kernel-metadata.json").read_text(encoding="utf-8"))
        assert meta == {"id": f"kurtvalcorza/{v['slug']}", "title": v["title"], "code_file": path.name,
                        "language": "python", "kernel_type": "notebook", "is_private": not v["public"],
                        "enable_gpu": True, "enable_tpu": False, "enable_internet": True, "dataset_sources": [],
                        "competition_sources": [], "kernel_sources": [],
                        "model_sources": [f"kurtvalcorza/rice-pest-detector/onnx/{v['kaggle_model']}/3"],
                        "keywords": bn.KAGGLE_KEYWORDS}
        assert len(meta["title"]) < 40
        assert re.sub(r"[^a-z0-9]+", "-", meta["title"].lower()).strip("-") == meta["id"].split("/")[1]
    for public in ("r50v5-kaggle", "rfdetr-m-kaggle"):  # public since 21 Oct 2026; a push must not make them private
        assert bn.VARIANTS[public]["public"]


def test_each_edition_links_its_own_published_model(built):
    expected = {"r50v5-kaggle": "r50-v5", "rfdetr-m-kaggle": "rf-detr-m", "dfine-l-kaggle": "d-fine-l"}
    for variant, (path, nb) in built.items():
        url = f"https://www.kaggle.com/models/kurtvalcorza/rice-pest-detector/onnx/{expected[variant]}"
        assert bn.VARIANTS[variant]["kaggle_model"] == expected[variant]
        assert f"]({url})" in _cell(nb, "intro")
        assert "kaggle.com/models/kurtvalcorza/rice-pest-detector" in _cell(nb, "references")


def test_a_public_variant_writes_is_private_false(tmp_path, monkeypatch):
    monkeypatch.setitem(bn.VARIANTS, "r50v5-kaggle", {**bn.VARIANTS["r50v5-kaggle"], "public": True})
    path = bn.build(tmp_path / "nb.ipynb", variant="r50v5-kaggle")
    assert json.loads((path.parent / "kernel-metadata.json").read_text())["is_private"] is False
    assert json.loads((path.parent / "declaration.json").read_text())["kaggle"]["is_private"] is False


def test_declaration_hashes_are_recomputable(built):
    lock_sha = hashlib.sha256(bn.LOCK_PATH.read_text(encoding="utf-8").encode()).hexdigest()
    for variant, (path, _) in built.items():
        decl = json.loads((path.parent / "declaration.json").read_text(encoding="utf-8"))
        assert decl["variant"] == variant
        assert decl["notebook_sha256"] == hashlib.sha256(path.read_bytes()).hexdigest()
        raw = json.loads(path.read_bytes())
        joined = "\n\0".join("".join(c["source"]) for c in raw["cells"])
        assert decl["cell_sources_sha256"] == hashlib.sha256(joined.encode()).hexdigest()
        assert decl["lock"] == {"path": "notebooks/kaggle/requirements-kaggle.lock.txt", "sha256": lock_sha,
                                "uv": "0.12.15", "python": "3.12.12", "platform": "x86_64-manylinux_2_28"}
        for rel, digest in decl["embedded"].items():
            p = ROOT / rel
            data = p.read_bytes() if rel.startswith("data/") else p.read_text(encoding="utf-8").encode()
            assert hashlib.sha256(data).hexdigest() == digest, rel
        assert "src/rice_pest_detector/train.py" in decl["embedded"] and "tools/kaggle_driver.py" in decl["embedded"]
        assert set(decl["generator"]) == {"tools/build_notebook.py", "tools/kaggle_cells.py"}
        assert decl["kaggle"]["accelerator"] == "NvidiaTeslaT4"
        assert decl["kaggle"]["is_private"] is not bn.VARIANTS[variant]["public"]


# ------------------------------------------------------------------ runtime cell (T017)


def test_runtime_cell_is_first_code_and_uses_the_standard_library_only(built):
    for _, nb in built.values():
        first_code = next(c for c in nb.cells if c.cell_type == "code")
        assert first_code["id"] == "runtime"
        src = first_code.source
        modules = {a.name.split(".")[0] for node in ast.walk(ast.parse(src))
                   if isinstance(node, (ast.Import, ast.ImportFrom))
                   for a in (node.names if isinstance(node, ast.Import) else [ast.alias(node.module)])}
        assert modules <= set(sys.stdlib_module_names)
        assert src.index("platform.machine()") < src.index("nvidia-smi") < src.index("zenodo.org")
        assert "'T4' not in GPUS[0]" in src and "GPU T4" in src and "Internet on" in src
        assert "Linux x86_64" in src and "shutil.disk_usage" in src and "/kaggle/working" in src


# ------------------------------------------------------------------ carrier cell (T018)


def test_carrier_pins_uv_and_installs_only_the_hashed_lock(built):
    for _, nb in built.values():
        src = _cell(nb, "carrier")
        assert kc.UV_URL in src and kc.UV_SHA256 in src and "UV_BYTES = 20081404" in src
        assert src.index("hashlib.sha256(_wheel)") < src.index("UV.write_bytes")
        assert "'venv', '--managed-python', '--python', '3.12.12'" in src
        assert "'--require-hashes', '--only-binary', ':all:'" in src and "-r', str(LOCK)" in src
        for key in ("HF_TOKEN", "HUGGING_FACE_HUB_TOKEN", "PYTHONPATH", "PYTHONHOME", "PYTHONSTARTUP"):
            assert f"'{key}'" in src
        assert "torch.cuda.is_available()" in src and "def run_stage(stage, *options)" in src
        assert src.count("'install'") == 1  # one install, from the lock


def test_lock_is_carried_byte_identical(built):
    lock_text = bn.LOCK_PATH.read_text(encoding="utf-8")
    for _, nb in built.values():
        first, body = _cell(nb, "lock").split("\n", 1)
        assert first == "%%writefile /tmp/rpd/requirements-kaggle.lock.txt"
        assert hashlib.sha256(body.encode()).hexdigest() == hashlib.sha256(lock_text.encode()).hexdigest()


def test_kernel_never_installs_or_imports_heavy_packages(built):
    for variant, (_, nb) in built.items():
        for src in _kernel_code(nb):
            assert "pip install" not in src and "!pip" not in src and "%pip" not in src
            for node in ast.walk(ast.parse(src)):
                if isinstance(node, ast.Import):
                    assert not {a.name.split(".")[0] for a in node.names} & HEAVY, variant
                if isinstance(node, ast.ImportFrom):
                    assert (node.module or "").split(".")[0] not in HEAVY, variant


def test_carried_cell_checks_every_written_file(built):
    for _, nb in built.values():
        src = _cell(nb, "carried")
        table = ast.literal_eval(src.split("CARRIED = ", 1)[1].split("\nfor ", 1)[0])
        assert len(table) == len(bn.carried_files())
        assert "requirements-kaggle.lock.txt" in table and "kaggle_driver.py" in table
        assert "rpd_tools/export_onnx.py" in table and "data/split_manifest.json" in table


# ------------------------------------------------------------------ paths and fetch (T019)


def test_paths_scratch_and_outputs(built):
    for variant, (_, nb) in built.items():
        src = _cell(nb, "paths")
        run = bn.VARIANTS[variant]["run"]
        assert "WORK = '/tmp/rpd'" in src and f"RUN_DIR = '/kaggle/working/{run}'" in src
        assert "RESUME_FROM = ''  # @param" in src
    driver = (ROOT / "tools" / "kaggle_driver.py").read_text(encoding="utf-8")
    assert "/kaggle/working" not in driver.split('"""', 2)[2]  # code below the docstring writes where told
    assert 'self.images = self.work / "images"' in driver
    for _, nb in built.values():
        for src in _kernel_code(nb):
            assert "git clone" not in src and "files.upload" not in src


def test_attached_archive_is_used_only_when_all_three_pins_match(tmp_path):
    data = b"archive bytes"
    good = tmp_path / "input" / "a" / "deep" / "datasets.zip"
    bad = tmp_path / "input" / "b" / "datasets.zip"
    for p, payload in ((good, data), (bad, data + b"!")):
        p.parent.mkdir(parents=True)
        p.write_bytes(payload)
    pins = (len(data), hashlib.md5(data).hexdigest(), hashlib.sha256(data).hexdigest())
    assert kd.find_attached_archive(tmp_path / "input", *pins) == good
    bad_pins = (len(data), "0" * 32, pins[2])
    assert kd.find_attached_archive(tmp_path / "input", *bad_pins) is None
    assert kd.find_attached_archive(tmp_path / "missing", *pins) is None


# ------------------------------------------------------------------ write-up (T020)


def _treatment_words() -> list[str]:
    dart = (ROOT / "app" / "test" / "l10n_test.dart").read_text(encoding="utf-8")
    block = dart.split("const treatmentWords = [", 1)[1].split("];", 1)[0]
    return re.findall(r"'([^']+)'", block)


def test_write_up_layer(built):
    words = _treatment_words()
    assert "spray" in words
    for variant, (_, nb) in built.items():
        ids = [c["id"] for c in nb.cells]
        intro = _cell(nb, "intro")
        first_code = next(i for i, c in enumerate(nb.cells) if c.cell_type == "code")
        assert ids.index("intro") < first_code
        assert "> **Use notice.**" in intro
        assert "End-to-end reference notebook (E2E, REFERENCE)" in intro and "not a release-grade" in intro
        assert intro.count("\n1. ") == 1 and "\n8. " in intro  # objectives
        assert bn.VARIANTS[variant]["colab_time"] in intro and "12 hours" in intro and "quota" in intro
        assert "environment" in intro
        text = "\n".join(c.source for c in nb.cells if not _is_writefile(c.source) and "B64 = " not in c.source)
        for w in words:
            assert w not in text.lower(), (variant, w)
        assert "TODO" not in text and "WRITE ME" not in text and "placeholder" not in text.lower()
        assert "## What did not work" in _cell(nb, "did-not-work")
        refs = _cell(nb, "references")
        assert all(f"\n{n}. " in refs for n in range(1, 7)) and refs.count("](https://") >= 6
        prose = "\n".join(line for line in _markdown(nb).splitlines()
                          if not line.startswith("Data: ") and not line.startswith("1. Deleña"))
        assert prose.count("Deleña") == prose.count("its authors (Deleña et al.)") >= 1
        assert "workshop" not in _markdown(nb).lower()


def test_markdown_has_no_tabs_or_carriage_returns(built):
    for _, nb in built.values():
        assert "\t" not in _markdown(nb) and "\r" not in _markdown(nb)


# ------------------------------------------------------------------ validate and evaluate (T021)


def _manifest(n_val=3, dup=False, cls=0, boxes=1):
    images = []
    for split, n in (("train", 4948), ("val", 253), ("test", 252)):
        for i in range(n):
            images.append({"file": f"{split}{i}.jpg", "relative_path": f"{split}/{split}{i}.jpg", "split": split,
                           "width": 640, "height": 640, "boxes": [[cls, 0.5, 0.5, 0.1, 0.1]] * boxes})
    if dup:
        images[1]["file"] = images[0]["file"]
    return {"images": images}


def test_validation_checks_split_names_classes_and_query_ceiling():
    table, problems = kd.validation_problems(_manifest())
    assert problems == [] and table["split_sizes"] == kd.SPLIT_SIZES
    assert any("duplicate file names" in p for p in kd.validation_problems(_manifest(dup=True))[1])
    assert any("class ids" in p for p in kd.validation_problems(_manifest(cls=5))[1])
    assert any("queries" in p for p in kd.validation_problems(_manifest(boxes=301))[1])
    real = json.loads((ROOT / "data" / "split_manifest.json").read_text(encoding="utf-8"))
    table, problems = kd.validation_problems(real)
    assert problems == [] and table["max_insects_per_image"] <= 300
    sizes = {r["file"]: (r["width"], r["height"]) for r in real["images"]}
    sizes[real["images"][0]["file"]] = (1, 1)
    assert any("size" in p for p in kd.validation_problems(real, sizes)[1])


def test_edition_threshold_and_size_come_from_the_manifest(built):
    for variant in EDITIONS:
        manifest = json.loads((ROOT / "models" / bn.VARIANTS[variant]["manifest"]).read_text(encoding="utf-8"))
        ed = bn.kaggle_edition(variant)
        assert ed["threshold"] == manifest["threshold"] and ed["review_below"] == manifest["review_below"]
        assert ed["input_size"] == manifest["input_size"] and ed["epochs"] == 40 and ed["batch_size"] == 4


def test_evaluate_stage_writes_metrics_and_detections_and_no_remote_code():
    driver = (ROOT / "tools" / "kaggle_driver.py").read_text(encoding="utf-8")
    assert '"val_metrics.json"' in driver and '"val_detections.json"' in driver
    assert "count-nothing baseline" in driver
    sources = [p.read_text(encoding="utf-8") for p in [*ROOT.glob("src/**/*.py"), *ROOT.glob("tools/*.py")]]
    assert not any(re.search(r"trust_remote_code\s*=\s*True", s) for s in sources)


# ------------------------------------------------------------------ export and reload (T022)


def _det(cls=0, score=0.9, box=(0, 0, 10, 10)):
    return {"class_id": cls, "score": score, "x0": box[0], "y0": box[1], "x1": box[2], "y1": box[3]}


@pytest.mark.torch
@pytest.mark.onnx
def test_reload_judgement_enforces_the_score_tolerance_only_when_the_variant_says_so():
    pytest.importorskip("onnxruntime")
    pytest.importorskip("torch")
    onnx_side, torch_side = [[_det(score=0.900)]], [[_det(score=0.902)]]
    enforced = kd.compare_detections(onnx_side, torch_side, score_tolerance_enforced=True)
    assert enforced["verdict"] == "FAIL" and enforced["failures"][0]["check"] == "score difference"
    with pytest.raises(RuntimeError, match="score difference"):
        kd.judge_reload(enforced)
    waived = kd.compare_detections(onnx_side, torch_side, score_tolerance_enforced=False)
    assert waived["verdict"] == "PASS" and waived["per_photo"][0]["waived"]
    kept = kd.compare_detections([[_det(), _det(box=(20, 20, 30, 30))]], torch_side, score_tolerance_enforced=False)
    assert kept["verdict"] == "FAIL" and kept["failures"][0]["check"] == "kept detections"
    boxes = kd.compare_detections([[_det(box=(0, 0, 10, 12))]], [[_det()]], score_tolerance_enforced=False)
    assert boxes["verdict"] == "FAIL" and boxes["failures"][0]["check"] == "box overlap"


@pytest.fixture
def tiny_run(tmp_path, monkeypatch):
    torch = pytest.importorskip("torch")
    pytest.importorskip("onnxruntime")
    pytest.importorskip("transformers")
    from PIL import Image
    from transformers import RTDetrConfig

    from rice_pest_detector import train

    def tiny_config():
        return RTDetrConfig(num_labels=4, num_queries=300, encoder_layers=1, decoder_layers=1, d_model=32,
                            encoder_hidden_dim=32, decoder_in_channels=[32, 32, 32], use_pretrained_backbone=False,
                            initializer_range=0.2)

    monkeypatch.setattr(train, "_tiny_config", tiny_config)
    work, run = tmp_path / "work", tmp_path / "run"
    (work / "data").mkdir(parents=True)
    run.mkdir()
    rng = __import__("numpy").random.default_rng(0)
    records = []
    for i in range(kd.RELOAD_PHOTOS):
        rel = f"val/img{i}.png"
        (work / "images" / "val").mkdir(parents=True, exist_ok=True)
        Image.fromarray(rng.integers(0, 255, (48, 64, 3), dtype="uint8")).save(work / "images" / rel)
        records.append({"file": f"img{i}.png", "relative_path": rel, "split": "val", "width": 64, "height": 48,
                        "boxes": []})
    (work / "data" / "split_manifest.json").write_text(json.dumps({"images": records}))
    edition = {"variant": "tiny-kaggle", "base_model": "__tiny__", "revision": "none", "input_size": 640,
               "threshold": 0.0, "review_below": 0.5, "epochs": 1, "batch_size": 1,
               "score_tolerance_enforced": True, "score_waiver": None}
    (work / "edition.json").write_text(json.dumps(edition))

    def save_best(seed):
        torch.manual_seed(seed)
        model = train.build_model(kd.train_config(edition))
        torch.save({"model": model.state_dict(), "map50_species": 0.5, "epoch": 0}, run / "best.pt")

    return kd.Context(work, run), save_best


@pytest.mark.torch
@pytest.mark.onnx
def test_export_and_fresh_process_reload_pass_and_a_different_model_fails(tiny_run):
    ctx, save_best = tiny_run
    save_best(0)
    kd.stage_export(ctx)
    record = json.loads((ctx.run_dir / "export_record.json").read_text())
    assert record["bytes"] == (ctx.run_dir / "model.onnx").stat().st_size and record["opset"] == 17
    kd.stage_reload(ctx)
    report = json.loads((ctx.run_dir / "reload_check.json").read_text())
    assert report["verdict"] == "PASS" and report["photos"] == kd.RELOAD_PHOTOS
    assert report["detections_compared"] == kd.RELOAD_PHOTOS * 300  # threshold 0 keeps every query
    save_best(1)  # the ONNX file no longer matches the checkpoint
    with pytest.raises(RuntimeError, match="fresh-process ONNX reload check failed"):
        kd.stage_reload(ctx)


# ------------------------------------------------------------------ test look (T023)


def test_test_look_is_off_by_default_and_needs_no_hand_set_threshold(built):
    for _, nb in built.values():
        src = _cell(nb, "test-look")
        assert src.startswith('RUN_TEST_LOOK = False  # @param {type:"boolean"}')
        assert kc.TEST_LOOKS_SPENT in src and "run_stage('test-look')" in src
        assert "THRESHOLD = None" not in src and "raise" not in src
        assert "THRESHOLD = None" not in "\n".join(_kernel_code(nb))
    driver = (ROOT / "tools" / "kaggle_driver.py").read_text(encoding="utf-8")
    assert '"test_metrics_reproduction.json"' in driver and "check_cached_test(prior, identity)" in driver


# ------------------------------------------------------------------ summary (T024)


def _fake_run(tmp_path):
    work, run = tmp_path / "work", tmp_path / "run"
    work.mkdir()
    run.mkdir()
    (work / "edition.json").write_text(json.dumps(bn.kaggle_edition("r50v5-kaggle")))
    (work / "requirements-kaggle.lock.txt").write_text("x==1\n")
    (run / "stage_times.json").write_text(json.dumps({"environment": 300, "fetch": 1200, "fit": 20000}))
    (run / "history.jsonl").write_text("".join(json.dumps({"epoch": e, "skipped_updates": 1}) + "\n" for e in range(3)))
    (run / "best.json").write_text(json.dumps({"map50_species": 0.93, "epoch": 1}))
    (run / "val_metrics.json").write_text(json.dumps({"headline": {"map50_species": 0.93}}))
    (run / "reload_check.json").write_text(json.dumps({"photos": 10, "detections_compared": 140, "max_score_diff": 1e-6,
                                                       "min_iou": 0.9999, "score_tolerance_enforced": True,
                                                       "verdict": "PASS"}))
    (run / "best.pt").write_bytes(b"pt")
    (run / "model.onnx").write_bytes(b"onnx")
    return kd.Context(work, run)


def test_run_summary_has_the_contract_keys(tmp_path):
    ctx = _fake_run(tmp_path)
    summary = kd.build_summary(ctx, {"python": "3.12.12", "gpu": "Tesla T4", "gpu_count": 2})
    for key in ("schema", "status", "variant", "model", "environment", "runtime", "durations_s", "training",
                "validation", "artifacts", "reload_check", "outputs_total_bytes", "test_look"):
        assert key in summary
    assert summary["status"] == "PASS" and summary["test_look"] == "skipped"
    assert summary["environment"]["uv"] == "0.12.15" and summary["environment"]["build_seconds"] == 300
    assert summary["training"]["best_epoch"] == 1 and summary["training"]["skipped_updates_total"] == 3
    assert summary["artifacts"]["model.onnx"]["sha256"] == hashlib.sha256(b"onnx").hexdigest()
    assert summary["durations_s"]["total"] == 21500


def test_summary_fails_on_images_archives_or_the_budget(tmp_path, monkeypatch):
    ctx = _fake_run(tmp_path)
    (ctx.run_dir / "photo.JPG").write_bytes(b"x")
    with pytest.raises(RuntimeError, match="image file"):
        kd.build_summary(ctx, {})
    (ctx.run_dir / "photo.JPG").unlink()
    (ctx.run_dir / "datasets.zip").write_bytes(b"x")
    with pytest.raises(RuntimeError, match="archive"):
        kd.build_summary(ctx, {})
    (ctx.run_dir / "datasets.zip").unlink()
    monkeypatch.setattr(kd, "OUTPUT_BUDGET_BYTES", 5)
    with pytest.raises(RuntimeError, match="budget"):
        kd.build_summary(ctx, {})


# ------------------------------------------------------------------ resume (T025)


def test_resume_helper(tmp_path, capsys):
    run = tmp_path / "run"
    run.mkdir()
    assert kd.resume_from("", run) == {"resumed": False}
    assert list(run.iterdir()) == []
    earlier = tmp_path / "input" / "my-earlier-run" / "run-r50v5"
    earlier.mkdir(parents=True)
    for name in ("last.pt", "best.pt", "history.jsonl"):
        (earlier / name).write_bytes(name.encode())
    record = kd.resume_from(str(tmp_path / "input"), run)
    assert record["resumed"] and sorted(record["files"]) == ["best.pt", "history.jsonl", "last.pt"]
    assert (run / "last.pt").read_bytes() == b"last.pt"
    assert "can run code" in capsys.readouterr().out
    with pytest.raises(SystemExit, match="no last.pt"):
        kd.resume_from(str(tmp_path / "empty"), run)


# ------------------------------------------------------------------ run_stage (T026)


FAKE_DRIVER = """\
import sys
args = sys.argv[1:]
print('driver args', args)
stage = args[args.index('--stage') + 1]
print('line for', stage)
sys.exit(3 if stage == 'boom' else 0)
"""


def _kernel(tmp_path):
    work, run = tmp_path / "work", tmp_path / "run"
    work.mkdir()
    run.mkdir()
    (work / "kaggle_driver.py").write_text(FAKE_DRIVER)
    ns = {"Path": Path, "json": json, "time": time, "subprocess": subprocess, "PYTHON": sys.executable,
          "ENV": dict(os.environ), "WORK": str(work), "RUN_DIR": str(run)}
    exec(kc.RUN_STAGE_SOURCE, ns)  # noqa: S102 -- the same source the carrier cell defines in the kernel
    return ns, run


def test_run_stage_streams_saves_the_log_and_times_the_stage(tmp_path, capsys):
    ns, run = _kernel(tmp_path)
    ns["run_stage"]("fetch", "opt1")
    out = capsys.readouterr().out
    assert "line for fetch" in out and "'--run-dir'" in out and "'opt1'" in out
    assert "line for fetch" in (run / "fetch.log").read_text()
    assert "fetch" in json.loads((run / "stage_times.json").read_text())


def test_run_stage_raises_naming_the_stage_and_repeats_the_log(tmp_path, capsys):
    ns, run = _kernel(tmp_path)
    with pytest.raises(RuntimeError, match="Stage 'boom' failed \\(exit 3\\)"):
        ns["run_stage"]("boom")
    assert capsys.readouterr().out.count("line for boom") == 2  # streamed, then repeated
    assert (run / "boom.log").exists()


# ------------------------------------------------------------------ challengers (T045)


def test_challengers_use_their_own_size_threshold_and_tolerance(built):
    rf, df, r50 = (bn.kaggle_edition(v) for v in ("rfdetr-m-kaggle", "dfine-l-kaggle", "r50v5-kaggle"))
    assert rf["input_size"] == 576 and rf["threshold"] == 0.48 and rf["score_tolerance_enforced"] is True
    assert df["input_size"] == 640 and df["threshold"] == 0.5 and df["score_tolerance_enforced"] is False
    assert r50["threshold"] == 0.48 and r50["score_tolerance_enforced"] is True
    assert "18 Oct 2026" in df["score_waiver"]
    _, df_nb = built["dfine-l-kaggle"]
    assert "18 Oct 2026" in _cell(df_nb, "paths") and "waived" in _cell(df_nb, "did-not-work")
    _, rf_nb = built["rfdetr-m-kaggle"]
    assert "'input_size': 576" in _cell(rf_nb, "paths") and "576 × 576" in _cell(rf_nb, "problem")
    locks = {_cell(nb, "lock") for _, nb in built.values()}
    assert len(locks) == 1


def test_editions_fit_kaggle_source_limit(built):
    # Kaggle rejects a notebook source over 1 MB (SaveKernel 400, 2026-10-20); keep a margin.
    for variant, (path, _) in built.items():
        assert path.stat().st_size < 950_000, (variant, path.stat().st_size)


def test_data_cell_downloads_pinned_files_with_matching_hashes(built):
    import hashlib
    expected = {p.name: (p.stat().st_size, hashlib.sha256(p.read_bytes()).hexdigest())
                for p in sorted((ROOT / "data").glob("*.json"))}
    for variant, (_, nb) in built.items():
        src = _cell(nb, "data")
        assert bn.DATA_COMMIT in src and re.fullmatch(r"[0-9a-f]{40}", bn.DATA_COMMIT), variant
        assert "raw.githubusercontent.com/kurtvalcorza/rice-pest-detector" in src
        for name, (size, digest) in expected.items():
            assert f"{name!r}: ({size}, {digest!r})" in src, (variant, name)
        assert "B64 =" not in "".join(c.source for c in nb.cells), variant


def test_editions_name_a_kernel_for_papermill(built):
    # Kaggle executes with papermill, which fails at once without a kernelspec (2026-10-20, version 1).
    for variant, (_, nb) in built.items():
        assert nb.metadata["kernelspec"]["name"] == "python3", variant
