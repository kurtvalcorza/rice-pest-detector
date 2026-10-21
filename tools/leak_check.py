"""Leak check for the Kaggle editions and their run outputs (spec 010, FR-025).

Scans every file given (folders are walked; executed notebooks included) for developer-local paths, email addresses,
token patterns, `.env` assignments and, in committed notebooks, output cells. Terms specific to the owner are read
from an `--extra-terms` file kept outside the repository, so that the list itself is never published.

Run: python tools/leak_check.py notebooks/kaggle/<slug> [more paths] [--extra-terms <file>] [--allow-outputs]
Exit 0 with "0 hits", or 1 with each hit printed as <file>:<line>: <rule>.
"""

import argparse
import json
import re
import sys
from pathlib import Path

PATTERNS = {
    "windows drive path": re.compile(r"(?<![A-Za-z])[A-Za-z]:[\\/](?:Users|Documents and Settings|home)[\\/]", re.IGNORECASE),
    "user home path": re.compile(r"(?:/home/[a-z_][a-z0-9_-]*/|/Users/[A-Za-z][^/\s]*/|~/)"),
    "email address": re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"),
    "Hugging Face token": re.compile(r"\bhf_[A-Za-z0-9]{30,}\b"),
    "GitHub token": re.compile(r"\b(?:gh[pousr]_[A-Za-z0-9]{36,}|github_pat_[A-Za-z0-9_]{40,})\b"),
    "Kaggle key": re.compile(r"(?i)\"?(?:kaggle_?key|\"key\")\"?\s*[:=]\s*\"?[0-9a-f]{32}\b"),
    ".env assignment": re.compile(r"(?m)^\s*(?:export\s+)?[A-Z][A-Z0-9_]*(?:TOKEN|SECRET|PASSWORD|API_KEY)\s*=\s*\S+"),
}
TEXT_SUFFIXES = {".ipynb", ".json", ".md", ".txt", ".py", ".csv", ".log", ".yml", ".yaml", ".in", ".cfg", ".toml",
                 ".jsonl", ""}


def _files(paths: list[Path]) -> list[Path]:
    out = []
    for p in paths:
        if p.is_dir():
            out += sorted(f for f in p.rglob("*") if f.is_file())
        elif p.is_file():
            out.append(p)
        else:
            raise FileNotFoundError(p)
    return out


def _output_cells(path: Path, text: str) -> list[str]:
    try:
        nb = json.loads(text)
    except json.JSONDecodeError:
        return []
    hits = []
    for i, cell in enumerate(nb.get("cells", [])):
        if cell.get("outputs") or cell.get("execution_count") is not None:
            hits.append(f"{path}: cell {i} ({cell.get('id', '?')}): output cell in a committed notebook")
    return hits


def scan(paths: list[Path], extra_terms: list[str] = (), allow_outputs: bool = False) -> list[str]:
    hits = []
    terms = [t for t in (t.strip() for t in extra_terms) if t and not t.startswith("#")]
    for path in _files([Path(p) for p in paths]):
        hits += [f"{path}: file name matches an extra term" for t in terms if t.lower() in path.name.lower()]
        if path.suffix.lower() not in TEXT_SUFFIXES:
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        if path.suffix == ".ipynb" and not allow_outputs:
            hits += _output_cells(path, text)
        for n, line in enumerate(text.splitlines(), start=1):
            for rule, pattern in PATTERNS.items():
                hits += [f"{path}:{n}: {rule}" for _ in pattern.finditer(line)]
            low = line.lower()
            hits += [f"{path}:{n}: extra term" for t in terms if t.lower() in low]
    return hits


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("paths", nargs="+", type=Path)
    ap.add_argument("--extra-terms", type=Path, help="file of extra terms, one per line (kept outside the repository)")
    ap.add_argument("--allow-outputs", action="store_true", help="executed notebooks: outputs are expected")
    args = ap.parse_args(argv)
    terms = args.extra_terms.read_text(encoding="utf-8").splitlines() if args.extra_terms else []
    hits = scan(args.paths, terms, args.allow_outputs)
    for hit in hits:
        print(hit)
    print(f"{len(hits)} hits")
    return 1 if hits else 0


if __name__ == "__main__":
    sys.exit(main())
