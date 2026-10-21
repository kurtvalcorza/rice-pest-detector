import base64
import gzip
import hashlib
import re
from pathlib import Path

import nbformat

from tools.build_notebook import build

ROOT = Path(__file__).resolve().parents[1]


def _sources(nb) -> str:
    return "\n".join(c.source for c in nb.cells)


def _sources_without_data(nb) -> str:
    return "\n".join(c.source for c in nb.cells if "B64 = " not in c.source)


def test_notebook_embeds_every_module_and_pins_revision(tmp_path: Path):
    nb = nbformat.read(build(tmp_path / "nb.ipynb", revision="abc123"), as_version=4)
    sources = _sources(nb)
    modules = list((ROOT / "src" / "rice_pest_detector").glob("*.py"))
    assert modules
    for module in modules:
        assert f"%%writefile /content/rpd/rice_pest_detector/{module.name}" in sources
    assert 'revision="abc123"' in sources
    assert "transformers==4.57.6" in sources
    assert sources.count('split="test"') == 1  # test split evaluated exactly once


def test_notebook_has_no_outputs_or_tokens(tmp_path: Path):
    nb = nbformat.read(build(tmp_path / "nb.ipynb", revision="abc123"), as_version=4)
    assert all(not getattr(c, "outputs", []) for c in nb.cells)
    prose = _sources_without_data(nb).lower()
    assert "token" not in prose
    assert not re.search(r"hf_[A-Za-z0-9]{20,}", _sources(nb))


def test_notebook_is_small_and_deterministic(tmp_path: Path):
    first = build(tmp_path / "a.ipynb", revision="abc123")
    second = build(tmp_path / "b.ipynb", revision="abc123")
    assert first.stat().st_size < 10 * 1024 * 1024
    assert first.read_bytes() == second.read_bytes()


def test_embedded_data_decodes_to_original_bytes(tmp_path: Path):
    nb = nbformat.read(build(tmp_path / "nb.ipynb", revision="abc123"), as_version=4)
    embedded = {}
    for cell in nb.cells:
        match = re.search(r"/content/rpd/data/([\w.]+)", cell.source)
        if cell.cell_type == "code" and match and "B64" in cell.source:
            blob = re.search(r'B64 = """(.*?)"""', cell.source, re.DOTALL).group(1)
            embedded[match.group(1)] = gzip.decompress(base64.b64decode("".join(blob.split())))
    originals = sorted((ROOT / "data").glob("*.json"))
    assert sorted(embedded) == [p.name for p in originals]
    for path in originals:
        assert hashlib.sha256(embedded[path.name]).hexdigest() == hashlib.sha256(path.read_bytes()).hexdigest()


def test_test_eval_cell_guards_against_reevaluation(tmp_path: Path):
    nb = nbformat.read(build(tmp_path / "nb.ipynb", revision="abc123"), as_version=4)
    cell = next(c.source for c in nb.cells if 'split="test"' in c.source)
    assert "best_pt_sha256" in cell
    assert "test split already evaluated for this checkpoint" in cell
    assert "check_cached_test(prior, identity)" in cell  # raises on any setup mismatch
    assert "'evaluation': identity" in cell
    assert "'epoch'" in cell
    assert _sources(nb).count('split="test"') == 1


def test_notebook_stops_early_without_a_gpu(tmp_path: Path):
    nb = nbformat.read(build(tmp_path / "nb.ipynb", revision="abc123"), as_version=4)
    versions = next(c.source for c in nb.cells if c.get("id") == "versions")
    assert "torch.cuda.is_available()" in versions and "raise RuntimeError" in versions
    sources = [c.source for c in nb.cells]
    assert sources.index(versions) < next(i for i, s in enumerate(sources) if "fit(cfg" in s)


def test_fetch_cell_skips_verified_archive_and_versions_printed(tmp_path: Path):
    sources = _sources(nbformat.read(build(tmp_path / "nb.ipynb", revision="abc123"), as_version=4))
    assert "verified archive present, skipping download" in sources
    assert "transformers.__version__" in sources


def test_env_log_cell_follows_install_and_drive_cells(tmp_path: Path):
    nb = nbformat.read(build(tmp_path / "nb.ipynb", revision="abc123"), as_version=4)
    ids = [c["id"] for c in nb.cells]
    assert ids.index("drive") < ids.index("env") < ids.index("env-log")
    cell = next(c.source for c in nb.cells if c["id"] == "env-log")
    for needle in ("pip", "freeze", "nvidia-smi", "transformers.__version__", "torch.__version__",
                   "sys.version", "timezone.utc", "RUN_DIR", "env-"):
        assert needle in cell
    compile(cell, "env-log", "exec")


def test_drive_cell_reports_free_space_and_warns(tmp_path: Path):
    nb = nbformat.read(build(tmp_path / "nb.ipynb", revision="abc123"), as_version=4)
    cell = next(c.source for c in nb.cells if c["id"] == "drive")
    assert "shutil.disk_usage('/content/drive')" in cell
    assert "< 20" in cell and "WARNING" in cell
    assert "RUN_DIR" in cell


def test_r50_variant_uses_its_own_model_run_dir_and_t4_batch(tmp_path: Path):
    nb = nbformat.read(build(tmp_path / "r50.ipynb", revision="def456", variant="r50"), as_version=4)
    sources = _sources_without_data(nb)
    assert 'base_model="PekingU/rtdetr_r50vd"' in sources and 'revision="def456"' in sources
    assert "rice-pest-detector/run-r50'" in sources and "run-r18" not in sources
    assert "batch_size=4" in sources and "epochs=40" in sources


def test_r50_test_look_waits_for_a_validation_chosen_threshold(tmp_path: Path):
    nb = nbformat.read(build(tmp_path / "r50.ipynb", revision="def456", variant="r50"), as_version=4)
    test_cell = next(c.source for c in nb.cells if c.get("id") == "test-eval")
    assert "THRESHOLD = None" in test_cell
    assert "raise RuntimeError" in test_cell.split("THRESHOLD = None", 1)[1].split("evaluation_id(", 1)[0]
    assert test_cell.count('split="test"') == 1


def test_r18_notebook_is_unchanged_by_the_variant_option(tmp_path: Path):
    default = build(tmp_path / "a.ipynb", revision="abc123")
    explicit = build(tmp_path / "b.ipynb", revision="abc123", variant="r18")
    assert default.read_bytes() == explicit.read_bytes()
    assert "rtdetr_r18vd" in _sources(nbformat.read(default, as_version=4))


def test_r50_skips_drive_mount_when_the_cli_already_mounted_it(tmp_path: Path):
    nb = nbformat.read(build(tmp_path / "r50.ipynb", revision="def456", variant="r50"), as_version=4)
    drive = next(c.source for c in nb.cells if c.get("id") == "drive")
    assert "if not os.path.isdir('/content/drive/MyDrive'):\n    drive.mount('/content/drive')" in drive


def test_r50_test_cell_checks_the_protocol_before_showing_cached_numbers_and_writes_atomically(tmp_path: Path):
    nb = nbformat.read(build(tmp_path / "r50.ipynb", revision="def456", variant="r50"), as_version=4)
    cell = next(c.source for c in nb.cells if c.get("id") == "test-eval")
    cached = cell.split("if metrics_path.exists():", 1)[1].split("else:", 1)[0]
    assert cached.index("check_cached_test(") < cached.index("print(json.dumps(prior")
    assert "_atomic_write_text(metrics_path" in cell and "metrics_path.write_text(" not in cell


def test_wave2_variants_pin_fixed_transformers_and_keep_the_r50_recipe(tmp_path: Path):
    for variant, model, run in (("r50v5", "PekingU/rtdetr_r50vd", "run-r50v5"),
                                ("dfine-l", "ustc-community/dfine-large-coco", "run-dfine-l")):
        nb = nbformat.read(build(tmp_path / f"{variant}.ipynb", revision="rev1", variant=variant), as_version=4)
        sources = _sources_without_data(nb)
        assert "transformers==5.20.1" in sources and "transformers==4.57.6" not in sources
        assert f'base_model="{model}"' in sources and f"rice-pest-detector/{run}'" in sources
        assert "batch_size=4" in sources and "epochs=40" in sources
        test_cell = next(c.source for c in nb.cells if c.get("id") == "test-eval")
        assert "THRESHOLD = None" in test_cell


def test_older_variants_keep_their_original_transformers_pin(tmp_path: Path):
    for variant in ("r18", "r50"):
        sources = _sources(nbformat.read(build(tmp_path / f"{variant}.ipynb", revision="x", variant=variant), as_version=4))
        assert "transformers==4.57.6" in sources and "5.20.1" not in sources


def test_rfdetr_variant_trains_and_tests_at_576(tmp_path: Path):
    nb = nbformat.read(build(tmp_path / "rf.ipynb", revision="rev2", variant="rfdetr-m"), as_version=4)
    sources = _sources_without_data(nb)
    assert 'base_model="Roboflow/rf-detr-medium"' in sources and "input_size=576" in sources
    assert "transformers==5.20.1" in sources and "rice-pest-detector/run-rfdetr-m'" in sources
    test_cell = next(c.source for c in nb.cells if c.get("id") == "test-eval")
    assert 'split="test", size=cfg.input_size)' in test_cell and "THRESHOLD = None" in test_cell
    other = nbformat.read(build(tmp_path / "d.ipynb", revision="rev1", variant="dfine-l"), as_version=4)
    assert "size=cfg.input_size" not in next(c.source for c in other.cells if c.get("id") == "test-eval")


COLAB_SHA256 = {  # recorded 2026-10-20 before spec 010 (baseline in docs/kaggle-runs/LEDGER.md)
    "train_colab.ipynb": "22bde1f00eed5dd831f935cf2ce49e6c94ad95f2875d4178c66bde220cb15f5f",
    "train_colab_r50.ipynb": "d16847486d7b827b6635314f4c03dde266bced47759c13746511d38353bf160e",
    "train_colab_r50v5.ipynb": "99f6711dea50eece1a4fc16393070914bac1ddf5684b01bc1fa64aa761b7c98c",
    "train_colab_dfine-l.ipynb": "663ba2052e67f7ea6a5a1b438f261d3a1ce49d038cc45b1476cd784bc58295df",
    "train_colab_rfdetr-m.ipynb": "267b287d2a71cd7a779a3463c8cb594707c6a4e5519c3bdfaa87d978d0f0880d",
}


def test_every_variant_records_its_revision_and_colab_notebooks_build_unchanged(tmp_path: Path):
    import tools.build_notebook as bn

    assert all(re.fullmatch(r"[0-9a-f]{40}", v["revision"]) for v in bn.VARIANTS.values())
    for variant in bn.COLAB_VARIANTS:
        target = bn.committed_path(variant)
        assert hashlib.sha256(target.read_bytes()).hexdigest() == COLAB_SHA256[target.name]
        fresh = build(tmp_path / target.name, variant=variant)  # revision from the variant table
        assert fresh.read_bytes() == target.read_bytes(), variant


def test_check_all_checks_every_committed_notebook_and_fails_on_any_difference(monkeypatch, capsys):
    import tools.build_notebook as bn

    seen = []
    monkeypatch.setattr(bn, "check", lambda variant, revision=None: seen.append(variant) or [])
    assert bn.check_all() == 0
    assert seen == [*bn.COLAB_VARIANTS, *bn.KAGGLE_VARIANTS] and len(seen) == 8
    assert "8 of 8 notebooks match" in capsys.readouterr().out
    monkeypatch.setattr(bn, "check", lambda variant, revision=None: ["x.ipynb"] if variant == "dfine-l-kaggle" else [])
    assert bn.check_all() == 1


def test_check_fails_on_a_one_byte_change(tmp_path: Path, monkeypatch):
    import tools.build_notebook as bn

    for variant in ("r50v5", "r50v5-kaggle"):
        original = bn.committed_path(variant)
        assert bn.check(variant) == []  # the committed files match a fresh build with the variant's own revision
        copy = tmp_path / variant / original.name
        copy.parent.mkdir()
        for name in (original.name, "kernel-metadata.json", "declaration.json"):
            if (original.parent / name).is_file():
                (copy.parent / name).write_bytes((original.parent / name).read_bytes())
        data = bytearray(copy.read_bytes())
        data[-2] ^= 1
        copy.write_bytes(bytes(data))
        monkeypatch.setattr(bn, "committed_path", lambda v, _c=copy: _c)
        assert bn.check(variant) == [original.name]
        monkeypatch.undo()


def test_new_variants_carry_the_dataset_credit_and_run_notebooks_stay_unchanged(tmp_path: Path, monkeypatch):
    import json

    import tools.build_notebook as bn

    rev = "df939e661d8c52e80608d1ec566561aabd25a4e7"
    monkeypatch.setitem(bn.VARIANTS, "credit-probe", dict(bn.VARIANTS["r50v5"], run="run-credit-probe"))
    fresh = json.loads(bn.build(tmp_path / "probe.ipynb", rev, "credit-probe").read_text(encoding="utf-8"))
    intro = "".join(fresh["cells"][0]["source"])
    assert "doi.org/10.5281/zenodo.20066074" in intro and "CC BY 4.0" in intro
    old = json.loads(bn.build(tmp_path / "r50v5.ipynb", rev, "r50v5").read_text(encoding="utf-8"))
    assert "zenodo" not in "".join(old["cells"][0]["source"])
