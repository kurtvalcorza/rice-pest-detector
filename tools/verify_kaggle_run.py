"""Independent checker for a Kaggle edition's run, ledger append and publication receipt (spec 010, FR-024, FR-026).

Verify a downloaded run (outputs plus the executed notebook) against the edition's build declaration:

    python tools/verify_kaggle_run.py runs/kaggle/r50v5 \
        --declaration notebooks/kaggle/rice-pest-detector-train-rt-detr-r50/declaration.json \
        [--notebook <executed .ipynb>] [--images <local validation images>] [--ledger docs/kaggle-runs/LEDGER.md]

Record the anonymous check after the owner has made an edition public:

    python tools/verify_kaggle_run.py receipt kurtvalcorza/<slug> --authorized <YYYY-MM-DD> --public-version <n> \
        --out docs/kaggle-runs/<variant>/receipt.json --ledger docs/kaggle-runs/LEDGER.md

The headline numbers are recomputed with the repository's own `metrics.py` from `val_detections.json`; they must
equal the printed ones exactly, then they are compared with the evaluation record within the tolerances fixed in
the spec's verification contract before the first run. A number outside its tolerance is a finding (DIFFERS) for
the owner, not an error.
"""

import argparse
import datetime
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools import build_notebook as bn
from tools import kaggle_driver as kd

LEDGER_HEADER = "| Date (UTC) | Edition | Kaggle version | Code commit | Source hash | GPU | Time | Verdict | Evidence |"
EXACT = 1e-9
BASELINE = 0.474
# Recorded validation figures (docs/evaluation-record.md, wave 2 and D-FINE-L) and the fixed tolerances.
RECORDED = {
    "r50v5-kaggle": {"best_val_map50_species": 0.937, "map50_four_class": 0.861, "count_accuracy": 0.834,
                     "wsb30_mae": 8.67, "onnx_bytes": 171_744_970, "best_epoch": 1},
    "rfdetr-m-kaggle": {"best_val_map50_species": 0.933, "map50_four_class": 0.837, "count_accuracy": 0.846,
                        "wsb30_mae": 9.56, "onnx_bytes": 121_956_743, "best_epoch": 3},
    "dfine-l-kaggle": {"best_val_map50_species": 0.940, "map50_four_class": 0.848, "count_accuracy": 0.822,
                       "wsb30_mae": 8.56, "onnx_bytes": 125_213_572, "best_epoch": 3},
}
TOLERANCE = {"best_val_map50_species": 0.02, "map50_four_class": 0.03, "count_accuracy": 0.04, "wsb30_mae": 2.0,
             "onnx_bytes": 0.01}  # onnx_bytes: relative
EXPECTED_OUTPUTS = ("run_summary.json", "val_metrics.json", "val_detections.json", "best.pt", "best.json",
                    "history.jsonl", "model.onnx", "export_record.json", "reload_check.json",
                    "reload_onnx_detections.json", "predictions_val_sample.csv")
USER_AGENT = "Mozilla/5.0 (compatible; anonymous-visibility-check)"


def recompute(detections: dict, manifest: dict) -> dict:
    """Headline validation numbers from the saved raw detections, with the repository's metric code."""
    from rice_pest_detector.metrics import count_accuracy, count_errors, map50, species_counts

    records = [r for r in manifest["images"] if r["split"] == "val"]
    coco = json.loads((ROOT / "data" / "annotations_val.json").read_text(encoding="utf-8"))
    threshold = detections["threshold"]
    by_file = {img["file"]: img for img in detections["images"]}
    dets, preds, refs = [], [], []
    for image_id, rec in enumerate(records, start=1):
        found = by_file[rec["file"]]["detections"]
        dets += [{"image_id": image_id, **d} for d in found]
        preds.append(species_counts([d["category_id"] - 1 for d in found if d["score"] >= threshold]))
        refs.append(species_counts([b[0] for b in rec["boxes"]]))
    by_class = {k: v for k, v in map50(coco, dets, group_species=False).items() if k != "all"}
    errors = count_errors(preds, refs)
    return {"map50_species": map50(coco, dets, group_species=True)["all"],
            "map50_four_class": sum(by_class.values()) / len(by_class), "map50_by_class": by_class,
            "count_accuracy": count_accuracy(preds, refs),
            "count_accuracy_no_detection_baseline": count_accuracy([species_counts([]) for _ in refs], refs),
            "mae": {"rbb": errors["RBB"]["mae"], "wsb": errors["WSB"]["mae"]},
            "wsb30_mae": errors["WSB"]["mae_by_density"]["30+"]["mae"],
            "wsb30_images": errors["WSB"]["mae_by_density"]["30+"]["images"]}


def _equal(a, b) -> bool:
    if isinstance(a, dict) and isinstance(b, dict):
        return a.keys() == b.keys() and all(_equal(a[k], b[k]) for k in a)
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        return abs(a - b) <= EXACT
    return a == b


def compare(variant: str, summary: dict) -> list[dict]:
    rec, out = RECORDED[variant], []
    observed = {"best_val_map50_species": summary["training"]["best_val_map50_species"],
                "map50_four_class": summary["validation"]["map50_four_class"],
                "count_accuracy": summary["validation"]["count_accuracy"],
                "wsb30_mae": summary["validation"]["wsb30_mae"],
                "onnx_bytes": summary["artifacts"]["model.onnx"]["bytes"]}
    for metric, value in observed.items():
        tol = TOLERANCE[metric]
        limit = tol * rec[metric] if metric == "onnx_bytes" else tol
        within = value is not None and abs(value - rec[metric]) <= limit + EXACT
        out.append({"metric": metric, "kaggle": value, "recorded": rec[metric],
                    "tolerance": f"±{tol:.0%}" if metric == "onnx_bytes" else tol,
                    "verdict": "WITHIN" if within else "OUTSIDE"})
    baseline = summary["validation"]["count_accuracy_no_detection_baseline"]
    out.append({"metric": "count_accuracy_no_detection_baseline", "kaggle": baseline, "recorded": BASELINE,
                "tolerance": "exact to 3 places", "verdict": "WITHIN" if round(baseline, 3) == BASELINE else "OUTSIDE"})
    out.append({"metric": "best_epoch", "kaggle": summary["training"]["best_epoch"], "recorded": rec["best_epoch"],
                "tolerance": "recorded, not compared", "verdict": "RECORDED"})
    return out


def _executed_notebook(run_dir: Path, notebook: Path | None) -> Path | None:
    if notebook:
        return notebook
    found = sorted(run_dir.glob("*.ipynb"))
    return found[0] if found else None


def verify(run_dir: Path, declaration: dict, notebook: Path | None = None, images: Path | None = None,
           kernel_version: int | None = None, code_commit: str | None = None) -> dict:
    run_dir = Path(run_dir)
    variant = declaration["variant"]
    findings, failed = [], []
    result = {"variant": variant, "kernel": declaration["kaggle"]["id"], "kernel_version": kernel_version,
              "code_commit": code_commit}
    nb_path = _executed_notebook(run_dir, notebook)
    if nb_path is None or not nb_path.is_file():
        failed.append("executed notebook missing")
        observed, errors = None, None
    else:
        nb = json.loads(nb_path.read_text(encoding="utf-8"))
        observed = bn.cell_sources_sha256(nb)
        errors = sum(o.get("output_type") == "error" for c in nb["cells"] for o in c.get("outputs", []))
    result["source"] = {"declared": declaration["cell_sources_sha256"], "observed": observed,
                        "match": observed == declaration["cell_sources_sha256"]}
    if not result["source"]["match"]:
        failed.append("notebook source differs from the declaration")
    result["errors_in_executed_notebook"] = errors
    if errors:
        failed.append(f"{errors} error output(s) in the executed notebook")
    missing = [n for n in EXPECTED_OUTPUTS if not (run_dir / n).is_file()]
    if missing:
        failed.append("missing outputs: " + ", ".join(missing))
        result.update(verdict="FAILED", findings=failed)
        return result
    summary = json.loads((run_dir / "run_summary.json").read_text(encoding="utf-8"))
    lock = summary.get("environment", {}).get("lock_sha256")
    result["lock"] = {"declared": declaration["lock"]["sha256"], "observed": lock,
                      "match": lock == declaration["lock"]["sha256"]}
    if not result["lock"]["match"]:
        failed.append("lock differs from the declaration")
    gpu = summary.get("runtime", {}).get("gpu") or ""
    result["gpu"] = gpu
    if "T4" not in gpu:
        failed.append(f"GPU {gpu!r} is not a T4")
    if summary.get("status") != "PASS":
        failed.append(f"run status {summary.get('status')!r}")
    result["artifacts"] = {}
    for name, rec in summary["artifacts"].items():
        ok = rec is not None and kd.sha256_file(run_dir / name) == rec["sha256"]
        result["artifacts"][name] = "match" if ok else "MISMATCH"
        if not ok:
            failed.append(f"{name} hash differs from run_summary.json")
    manifest = json.loads((ROOT / "data" / "split_manifest.json").read_text(encoding="utf-8"))
    recomputed = recompute(json.loads((run_dir / "val_detections.json").read_text(encoding="utf-8")), manifest)
    printed = {k: summary["validation"].get(k) for k in recomputed}
    result["recomputed_equal"] = _equal(recomputed, printed)
    if not result["recomputed_equal"]:
        diff = [k for k in recomputed if not _equal(recomputed[k], printed[k])]
        failed.append("recomputed numbers differ from the printed ones: " + ", ".join(diff))
    result["comparisons"] = compare(variant, summary)
    findings += [f"{c['metric']}: {c['kaggle']} vs recorded {c['recorded']} (tolerance {c['tolerance']})"
                 for c in result["comparisons"] if c["verdict"] == "OUTSIDE"]
    result["local_onnx_check"] = local_onnx_check(run_dir, manifest, declaration, images)
    if result["local_onnx_check"] == "FAIL":
        failed.append("local ONNX check failed")
    result["training_seconds"] = summary.get("durations_s", {}).get("total")
    result["verdict"] = "FAILED" if failed else "DIFFERS" if findings else "VERIFIED"
    result["findings"] = failed + findings
    return result


def local_onnx_check(run_dir: Path, manifest: dict, declaration: dict, images: Path | None) -> str:
    """Run the downloaded ONNX file on CPU on the reload-check photos and compare with the notebook's detections."""
    if images is None:
        return "SKIPPED (no images)"
    edition = bn.kaggle_edition(declaration["variant"], declaration["model"]["revision"])
    records = [r for r in manifest["images"] if r["split"] == "val"][:kd.RELOAD_PHOTOS]
    ours = kd.onnx_detect(run_dir / "model.onnx", records, Path(images), edition["input_size"], edition["threshold"])
    theirs = json.loads((run_dir / "reload_onnx_detections.json").read_text(encoding="utf-8"))
    report = kd.compare_detections(ours, theirs, edition["score_tolerance_enforced"])
    return report["verdict"]


# ---------------------------------------------------------------- ledger and edition status


def ledger_rows(text: str) -> list[dict]:
    keys = ["date", "edition", "version", "commit", "source", "gpu", "time", "verdict", "evidence"]
    rows = []
    for line in text.splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) == len(keys) and cells[0][:2] == "20":
            rows.append(dict(zip(keys, cells, strict=True)))
    return rows


def append_ledger(ledger: Path, row: dict) -> None:
    """Append one row; existing rows are never edited (corrections are new rows)."""
    ledger = Path(ledger)
    text = ledger.read_text(encoding="utf-8") if ledger.exists() else ""
    if LEDGER_HEADER not in text:
        raise ValueError(f"{ledger} has no ledger table header")
    line = "| " + " | ".join(str(row[k]) for k in ("date", "edition", "version", "commit", "source", "gpu", "time",
                                                    "verdict", "evidence")) + " |\n"
    with ledger.open("a", encoding="utf-8", newline="\n") as fh:
        fh.write(("" if text.endswith("\n") else "\n") + line)


def edition_status(ledger_text: str, declaration: dict) -> dict:
    """Current state of an edition: rows for an older source (the lock is carried in the sources) are history."""
    source = declaration["cell_sources_sha256"][:12]
    rows = [r for r in ledger_rows(ledger_text) if r["edition"] == declaration["variant"]]
    current = [r for r in rows if r["source"].rstrip("…").startswith(source) or source.startswith(r["source"].rstrip("…"))]
    verdicts = [r["verdict"] for r in current]
    state = "public" if "PUBLIC" in verdicts else "verified" if "VERIFIED" in verdicts else "candidate"
    return {"state": state, "current": current, "history": [r for r in rows if r not in current]}


def _row(result: dict, evidence: str) -> dict:
    seconds = result.get("training_seconds")
    return {"date": datetime.datetime.now(datetime.UTC).strftime("%Y-%m-%d"), "edition": result["variant"],
            "version": result.get("kernel_version") or "?", "commit": (result.get("code_commit") or "?")[:7],
            "source": (result["source"]["observed"] or "none")[:12] + "…", "gpu": result.get("gpu") or "?",
            "time": f"{seconds / 3600:.1f} h" if seconds else "?", "verdict": result["verdict"],
            "evidence": evidence}


# ---------------------------------------------------------------- receipt


def http_get(url: str) -> tuple[int, bytes]:
    """Anonymous GET: no credentials, no cookies, a generic User-Agent."""
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            return response.status, response.read()
    except urllib.error.HTTPError as exc:
        return exc.code, b""


def receipt(ref: str, ledger: Path, authorized: str, public_version: int) -> dict:
    owner, slug = ref.split("/", 1)
    variant = next((v for v, k in bn.KAGGLE_VARIANTS.items() if k["slug"] == slug), None)
    if variant is None:
        raise ValueError(f"{ref} is not a Kaggle edition of this project")
    rows = ledger_rows(Path(ledger).read_text(encoding="utf-8"))
    verified = [r for r in rows if r["edition"] == variant and r["verdict"] == "VERIFIED"]
    if not verified:
        raise RuntimeError(f"{variant} has no VERIFIED run in the ledger; no receipt is written before verification")
    page_status, _ = http_get(f"https://www.kaggle.com/code/{owner}/{slug}")
    api_status, body = http_get(f"https://www.kaggle.com/api/v1/kernels/pull?userName={owner}&kernelSlug={slug}")
    try:
        is_private = json.loads(body)["metadata"]["isPrivate"] if api_status == 200 else None
    except (ValueError, KeyError, TypeError):
        is_private = None
    return {"ref": ref, "authorized_by": f"owner, {authorized} (route: Share → Public in the Kaggle interface)",
            "public_version": public_version,
            "verified_run": f"docs/kaggle-runs/{verified[-1]['evidence']} (VERIFIED)",
            "anonymous_page_http": page_status, "anonymous_api_http": api_status,
            "anonymous_api_is_private": is_private, "new_version_created": False,
            "metadata_updated": ("generator variant public=True; kernel-metadata.json is_private false"
                                 if bn.KAGGLE_VARIANTS[variant]["public"] else
                                 "not yet: generator variant public=False; kernel-metadata.json is_private true")}


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv and argv[0] == "receipt":
        ap = argparse.ArgumentParser(prog="verify_kaggle_run.py receipt")
        ap.add_argument("ref")
        ap.add_argument("--authorized", required=True, help="date the owner made the edition public")
        ap.add_argument("--public-version", type=int, required=True)
        ap.add_argument("--out", type=Path, required=True)
        ap.add_argument("--ledger", type=Path, required=True)
        args = ap.parse_args(argv[1:])
        rec = receipt(args.ref, args.ledger, args.authorized, args.public_version)
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(rec, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
        ok = rec["anonymous_page_http"] == 200 and rec["anonymous_api_http"] == 200 and rec["anonymous_api_is_private"] is False
        variant = next(v for v, k in bn.KAGGLE_VARIANTS.items() if k["slug"] == args.ref.split("/", 1)[1])
        verified = [r for r in ledger_rows(args.ledger.read_text(encoding="utf-8"))
                    if r["edition"] == variant and r["verdict"] == "VERIFIED"][-1]  # the run the receipt rests on
        append_ledger(args.ledger, {"date": datetime.datetime.now(datetime.UTC).strftime("%Y-%m-%d"),
                                    "edition": variant, "version": args.public_version, "commit": verified["commit"],
                                    "source": verified["source"], "gpu": "-", "time": "-",
                                    "verdict": "PUBLIC" if ok else "NOT-PUBLIC",
                                    "evidence": f"{variant.removesuffix('-kaggle')}/receipt.json"})
        print(json.dumps(rec, indent=1))  # ASCII escapes: a Windows console cannot print every character
        return 0 if ok else 1
    ap = argparse.ArgumentParser(description="Verify a downloaded Kaggle edition run")
    ap.add_argument("run_dir", type=Path)
    ap.add_argument("--declaration", type=Path, required=True)
    ap.add_argument("--notebook", type=Path)
    ap.add_argument("--images", type=Path)
    ap.add_argument("--kernel-version", type=int)
    ap.add_argument("--code-commit")
    ap.add_argument("--out", type=Path)
    ap.add_argument("--ledger", type=Path)
    args = ap.parse_args(argv)
    declaration = json.loads(args.declaration.read_text(encoding="utf-8"))
    result = verify(args.run_dir, declaration, args.notebook, args.images, args.kernel_version, args.code_commit)
    short = declaration["variant"].removesuffix("-kaggle")
    out = args.out or ROOT / "docs" / "kaggle-runs" / short / "verification.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=1) + "\n", encoding="utf-8")
    if args.ledger:
        append_ledger(args.ledger, _row(result, f"{short}/{out.name}"))
    print(json.dumps(result, indent=1))
    return 0 if result["verdict"] == "VERIFIED" else 1


if __name__ == "__main__":
    sys.exit(main())

