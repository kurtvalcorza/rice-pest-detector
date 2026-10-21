"""Independent checker, ledger and receipt for the Kaggle editions (spec 010, FR-024, FR-026), on synthetic runs."""

import hashlib
import json
import shutil
from pathlib import Path

import pytest

import tools.verify_kaggle_run as vk
from tools import build_notebook as bn

pytest.importorskip("pycocotools")

ROOT = Path(__file__).resolve().parents[1]
VARIANT = "r50v5-kaggle"
LEDGER = f"""# Kaggle runs

{vk.LEDGER_HEADER}
| :-- | :-- | :-- | :-- | :-- | :-- | :-- | :-- | :-- |
"""


def _declaration() -> dict:
    return json.loads((bn.committed_path(VARIANT).parent / "declaration.json").read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def perfect():
    """Detections equal to the ground truth, and the numbers the repository's metric code gives for them."""
    coco = json.loads((ROOT / "data" / "annotations_val.json").read_text(encoding="utf-8"))
    files = {img["id"]: img["file_name"] for img in coco["images"]}
    images = {i: [] for i in files}
    for a in coco["annotations"]:
        images[a["image_id"]].append({"category_id": a["category_id"], "score": 0.9, "bbox": a["bbox"]})
    dets = {"threshold": 0.48, "score_floor": 0.0,
            "images": [{"image_id": i, "file": files[i], "detections": d} for i, d in images.items()]}
    manifest = json.loads((ROOT / "data" / "split_manifest.json").read_text(encoding="utf-8"))
    return dets, vk.recompute(dets, manifest)


@pytest.fixture
def run(tmp_path, perfect, monkeypatch):
    dets, numbers = perfect
    decl = _declaration()
    run_dir = tmp_path / "r50v5"
    run_dir.mkdir()
    shutil.copy(bn.committed_path(VARIANT), run_dir / "executed.ipynb")
    (run_dir / "val_detections.json").write_text(json.dumps(dets))
    for name in ("val_metrics.json", "best.json", "history.jsonl", "export_record.json", "reload_check.json",
                 "reload_onnx_detections.json", "predictions_val_sample.csv"):
        (run_dir / name).write_text("{}")
    (run_dir / "best.pt").write_bytes(b"weights")
    (run_dir / "model.onnx").write_bytes(b"onnx")
    summary = {"schema": 1, "status": "PASS", "variant": VARIANT,
               "environment": {"uv": "0.12.15", "lock_sha256": decl["lock"]["sha256"]},
               "runtime": {"gpu": "Tesla T4", "gpu_count": 2}, "durations_s": {"total": 23000},
               "training": {"best_epoch": 2, "best_val_map50_species": numbers["map50_species"]},
               "validation": numbers,
               "artifacts": {"best.pt": {"bytes": 7, "sha256": hashlib.sha256(b"weights").hexdigest()},
                             "model.onnx": {"bytes": 4, "sha256": hashlib.sha256(b"onnx").hexdigest()}}}
    (run_dir / "run_summary.json").write_text(json.dumps(summary))
    recorded = {"best_val_map50_species": numbers["map50_species"], "map50_four_class": numbers["map50_four_class"],
                "count_accuracy": numbers["count_accuracy"], "wsb30_mae": numbers["wsb30_mae"], "onnx_bytes": 4,
                "best_epoch": 1}
    monkeypatch.setitem(vk.RECORDED, VARIANT, recorded)
    monkeypatch.setattr(vk, "BASELINE", round(numbers["count_accuracy_no_detection_baseline"], 3))
    return run_dir, decl, summary


def _rewrite(run_dir: Path, change):
    path = run_dir / "run_summary.json"
    summary = json.loads(path.read_text())
    change(summary)
    path.write_text(json.dumps(summary))


def test_matching_run_is_verified(run):
    run_dir, decl, _ = run
    result = vk.verify(run_dir, decl, kernel_version=1, code_commit="abc1234def")
    assert result["source"]["match"] and result["lock"]["match"] and result["recomputed_equal"]
    assert result["artifacts"] == {"best.pt": "match", "model.onnx": "match"}
    assert result["errors_in_executed_notebook"] == 0 and result["gpu"] == "Tesla T4"
    assert result["local_onnx_check"] == "SKIPPED (no images)"
    assert result["verdict"] == "VERIFIED", result["findings"]
    assert {c["verdict"] for c in result["comparisons"]} == {"WITHIN", "RECORDED"}


def test_source_mismatch_fails(run):
    run_dir, decl, _ = run
    nb = json.loads((run_dir / "executed.ipynb").read_text(encoding="utf-8"))
    nb["cells"][0]["source"] = "# edited by hand\n"
    (run_dir / "executed.ipynb").write_text(json.dumps(nb), encoding="utf-8")
    result = vk.verify(run_dir, decl)
    assert result["verdict"] == "FAILED" and not result["source"]["match"]


def test_kaggle_metadata_rewrites_do_not_change_the_source_hash(run):
    run_dir, decl, _ = run
    nb = json.loads((run_dir / "executed.ipynb").read_text(encoding="utf-8"))
    nb["metadata"]["kaggle"]["isGpuEnabled"] = True
    nb["cells"][2]["outputs"] = [{"output_type": "stream", "name": "stdout", "text": ["ok\n"]}]
    (run_dir / "executed.ipynb").write_text(json.dumps(nb), encoding="utf-8")
    assert vk.verify(run_dir, decl)["verdict"] == "VERIFIED"


@pytest.mark.parametrize("change, finding", [
    (lambda s: s["environment"].update(lock_sha256="0" * 64), "lock differs"),
    (lambda s: s["runtime"].update(gpu="Tesla P100-PCIE-16GB"), "not a T4"),
    (lambda s: s["artifacts"]["model.onnx"].update(sha256="0" * 64), "model.onnx hash"),
    (lambda s: s["validation"].update(count_accuracy=s["validation"]["count_accuracy"] + 0.001), "recomputed"),
])
def test_hard_failures(run, change, finding):
    run_dir, decl, _ = run
    _rewrite(run_dir, change)
    result = vk.verify(run_dir, decl)
    assert result["verdict"] == "FAILED" and any(finding in f for f in result["findings"]), result["findings"]


def test_error_output_and_missing_output_fail(run):
    run_dir, decl, _ = run
    nb = json.loads((run_dir / "executed.ipynb").read_text(encoding="utf-8"))
    nb["cells"][2]["outputs"] = [{"output_type": "error", "ename": "RuntimeError", "evalue": "x", "traceback": []}]
    (run_dir / "executed.ipynb").write_text(json.dumps(nb), encoding="utf-8")
    assert vk.verify(run_dir, decl)["errors_in_executed_notebook"] == 1
    (run_dir / "reload_check.json").unlink()
    result = vk.verify(run_dir, decl)
    assert result["verdict"] == "FAILED" and any("reload_check.json" in f for f in result["findings"])


def test_outside_tolerance_is_a_finding_not_an_error(run, monkeypatch):
    run_dir, decl, _ = run
    recorded = dict(vk.RECORDED[VARIANT])
    recorded["wsb30_mae"] += 2.5
    recorded["best_val_map50_species"] -= 0.019  # inside ±0.02
    monkeypatch.setitem(vk.RECORDED, VARIANT, recorded)
    result = vk.verify(run_dir, decl)
    verdicts = {c["metric"]: c["verdict"] for c in result["comparisons"]}
    assert verdicts["wsb30_mae"] == "OUTSIDE" and verdicts["best_val_map50_species"] == "WITHIN"
    assert verdicts["best_epoch"] == "RECORDED"
    assert result["verdict"] == "DIFFERS" and any("wsb30_mae" in f for f in result["findings"])


def test_onnx_size_tolerance_is_relative(run, monkeypatch):
    run_dir, _, _ = run
    monkeypatch.setitem(vk.RECORDED, VARIANT, {**vk.RECORDED[VARIANT], "onnx_bytes": 1000})
    _rewrite(run_dir, lambda s: s["artifacts"]["model.onnx"].update(bytes=1010))
    assert {c["metric"]: c["verdict"] for c in vk.compare(VARIANT, json.loads(
        (run_dir / "run_summary.json").read_text()))}["onnx_bytes"] == "WITHIN"
    _rewrite(run_dir, lambda s: s["artifacts"]["model.onnx"].update(bytes=1011))
    assert {c["metric"]: c["verdict"] for c in vk.compare(VARIANT, json.loads(
        (run_dir / "run_summary.json").read_text()))}["onnx_bytes"] == "OUTSIDE"


def test_cli_writes_verification_and_appends_one_ledger_row(run, tmp_path):
    run_dir, decl, _ = run
    ledger = tmp_path / "LEDGER.md"
    ledger.write_text(LEDGER + "| 2026-10-01 | r50v5-kaggle | 0 | 0000000 | ffffffffffff… | Tesla T4 | 6.0 h | FAILED | x |\n", encoding="utf-8")
    before = ledger.read_text(encoding="utf-8")
    out = tmp_path / "verification.json"
    decl_path = bn.committed_path(VARIANT).parent / "declaration.json"
    code = vk.main([str(run_dir), "--declaration", str(decl_path), "--ledger", str(ledger), "--out", str(out),
                    "--kernel-version", "3", "--code-commit", "abc1234def"])
    assert code == 0 and json.loads(out.read_text())["verdict"] == "VERIFIED"
    after = ledger.read_text(encoding="utf-8")
    assert after.startswith(before) and len(after.splitlines()) == len(before.splitlines()) + 1
    row = vk.ledger_rows(after)[-1]
    assert row["verdict"] == "VERIFIED" and row["version"] == "3" and row["commit"] == "abc1234"
    assert row["source"] == decl["cell_sources_sha256"][:12] + "…" and row["time"] == "6.4 h"


def test_ledger_without_header_is_refused(tmp_path):
    ledger = tmp_path / "LEDGER.md"
    ledger.write_text("# no table\n", encoding="utf-8")
    with pytest.raises(ValueError):
        vk.append_ledger(ledger, {k: "x" for k in ("date", "edition", "version", "commit", "source", "gpu", "time",
                                                   "verdict", "evidence")})


# ------------------------------------------------------------------ edition status (T040)


def test_status_follows_the_source_hash():
    decl = _declaration()
    current = decl["cell_sources_sha256"][:12] + "…"
    rows = (f"| 2026-10-21 | {VARIANT} | 1 | a | 0123456789ab… | Tesla T4 | 6.4 h | VERIFIED | r50v5/v.json |\n")
    assert vk.edition_status(LEDGER + rows, decl)["state"] == "candidate"  # verified rows of an older source: history
    assert len(vk.edition_status(LEDGER + rows, decl)["history"]) == 1
    rows += f"| 2026-10-22 | {VARIANT} | 2 | b | {current} | Tesla T4 | 6.4 h | VERIFIED | r50v5/v.json |\n"
    assert vk.edition_status(LEDGER + rows, decl)["state"] == "verified"
    rows += f"| 2026-10-23 | {VARIANT} | 2 | b | {current} | - | - | PUBLIC | r50v5/receipt.json |\n"
    assert vk.edition_status(LEDGER + rows, decl)["state"] == "public"  # the receipt row carries its run's source


def test_metadata_only_change_keeps_the_edition_verified(tmp_path, monkeypatch):
    decl = _declaration()
    monkeypatch.setitem(bn.VARIANTS, VARIANT, {**bn.VARIANTS[VARIANT], "public": True})
    rebuilt = bn.build(tmp_path / "nb.ipynb", variant=VARIANT)
    new_decl = json.loads((rebuilt.parent / "declaration.json").read_text())
    assert new_decl["kaggle"]["is_private"] is False
    assert new_decl["cell_sources_sha256"] == decl["cell_sources_sha256"]
    rows = (f"| 2026-10-22 | {VARIANT} | 2 | b | {decl['cell_sources_sha256'][:12]}… | Tesla T4 | 6.4 h | VERIFIED "
            "| r50v5/v.json |\n")
    assert vk.edition_status(LEDGER + rows, new_decl)["state"] == "verified"


# ------------------------------------------------------------------ receipt (T049)


class _Response:
    def __init__(self, status, body=b""):
        self.status, self._body = status, body

    def read(self):
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def test_receipt_is_anonymous_and_records_page_api_and_private_flag(tmp_path, monkeypatch):
    seen = []

    def fake_urlopen(request, timeout=None):
        seen.append(request)
        if "/api/" in request.full_url:
            return _Response(200, json.dumps({"metadata": {"isPrivate": False}}).encode())
        return _Response(200)

    monkeypatch.setattr(vk.urllib.request, "urlopen", fake_urlopen)
    ledger = tmp_path / "LEDGER.md"
    ledger.write_text(LEDGER + f"| 2026-10-22 | {VARIANT} | 2 | b | abc… | Tesla T4 | 6.4 h | VERIFIED | r50v5/v.json |\n", encoding="utf-8")
    rec = vk.receipt("kurtvalcorza/rice-pest-detector-train-rt-detr-r50", ledger, "2026-10-25", 2)
    assert rec["anonymous_page_http"] == 200 and rec["anonymous_api_http"] == 200
    assert rec["anonymous_api_is_private"] is False and rec["public_version"] == 2
    assert rec["verified_run"] == "docs/kaggle-runs/r50v5/v.json (VERIFIED)"  # the ledger row's own evidence
    # the receipt reports the generator's own public flag, never a claim that it was updated
    assert rec["metadata_updated"].startswith("not yet") is not bn.KAGGLE_VARIANTS[VARIANT]["public"]
    assert len(seen) == 2
    for request in seen:
        headers = {k.lower(): v for k, v in request.header_items()}
        assert set(headers) == {"user-agent"} and headers["user-agent"] == vk.USER_AGENT
        assert "kaggle" not in headers["user-agent"].lower() and "python" not in headers["user-agent"].lower()


def test_no_receipt_without_a_verified_run(tmp_path, monkeypatch):
    monkeypatch.setattr(vk.urllib.request, "urlopen", lambda *a, **k: pytest.fail("no request expected"))
    ledger = tmp_path / "LEDGER.md"
    ledger.write_text(LEDGER + f"| 2026-10-22 | {VARIANT} | 2 | b | abc… | Tesla T4 | 6.4 h | DIFFERS | r50v5/v.json |\n", encoding="utf-8")
    with pytest.raises(RuntimeError, match="no VERIFIED run"):
        vk.receipt("kurtvalcorza/rice-pest-detector-train-rt-detr-r50", ledger, "2026-10-25", 2)
