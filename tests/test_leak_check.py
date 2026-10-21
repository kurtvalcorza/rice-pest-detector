"""Leak check (spec 010, FR-025): generic patterns in code, specific terms only from an untracked file."""

import json
from pathlib import Path

from tools.leak_check import main, scan

ROOT = Path(__file__).resolve().parents[1]
DRIVE = "C:" + chr(92).join(["", "Users", "someone", "x.txt"])
HOME = "/home/" + "someone/data"
EMAIL = "someone" + "@example.org"
HF = "hf_" + "A" * 34
GH = "ghp_" + "b" * 36
KAGGLE = '{"username": "x", "key": "' + "0123456789abcdef" * 2 + '"}'


def _hits(tmp_path: Path, text: str, name: str = "f.txt", **kw) -> list[str]:
    path = tmp_path / name
    path.write_text(text, encoding="utf-8")
    return scan([path], **kw)


def test_each_generic_pattern_is_caught(tmp_path: Path):
    cases = {"windows drive path": DRIVE, "user home path": HOME, "email address": EMAIL,
             "Hugging Face token": HF, "GitHub token": GH, "Kaggle key": KAGGLE, ".env assignment": "HF_TOKEN=abc"}
    for rule, text in cases.items():
        hits = _hits(tmp_path, f"line one\n{text}\n")
        assert any(h.endswith(f":2: {rule}") for h in hits), (rule, hits)


def test_output_cells_in_a_committed_notebook_are_hits(tmp_path: Path):
    nb = {"cells": [{"cell_type": "code", "id": "a", "source": "1", "outputs": [{"text": "x"}],
                     "execution_count": 1}], "metadata": {}, "nbformat": 4, "nbformat_minor": 5}
    assert any("output cell" in h for h in _hits(tmp_path, json.dumps(nb), "n.ipynb"))
    assert _hits(tmp_path, json.dumps(nb), "n.ipynb", allow_outputs=True) == []


def test_extra_terms_come_from_a_file_and_are_not_echoed(tmp_path: Path, capsys):
    (tmp_path / "terms.txt").write_text("# comment\nSecretProjectName\n", encoding="utf-8")
    (tmp_path / "ed").mkdir()
    (tmp_path / "ed" / "a.md").write_text("mentions secretprojectname here\n", encoding="utf-8")
    assert main([str(tmp_path / "ed"), "--extra-terms", str(tmp_path / "terms.txt")]) == 1
    out = capsys.readouterr().out
    assert "a.md:1: extra term" in out and "SecretProjectName" not in out and "1 hits" in out


def test_clean_folder_and_the_committed_editions_pass(tmp_path: Path, capsys):
    (tmp_path / "clean.md").write_text("A clean file with https://doi.org/10.5281/zenodo.20066074\n")
    assert main([str(tmp_path)]) == 0
    assert "0 hits" in capsys.readouterr().out
    assert main([str(ROOT / "notebooks" / "kaggle")]) == 0
