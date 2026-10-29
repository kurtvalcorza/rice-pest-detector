"""Guards for the advanced track: intentional bugs stay patches, and nothing runs them.

The regression patches under ``workshop/advanced/patches/`` exist to be applied by a learner in a
disposable worktree. These tests make sure they never become importable code in this repository,
that each one still applies to today's ``infer.py`` (checked on a copy, never imported or run), and
that the teaching scripts use only the standard library.
"""

import ast
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

TRACK = Path(__file__).resolve().parents[1]
ROOT = TRACK.parents[1]
PATCHES = TRACK / "patches"
TARGET = "src/rice_pest_detector/infer.py"


def _patches():
    return sorted(PATCHES.glob("*.patch"))


def _changed_paths(patch_text):
    paths = set()
    for line in patch_text.splitlines():
        if line.startswith(("--- ", "+++ ")):
            path = line[4:].split("\t")[0].strip()
            if path != "/dev/null":
                paths.add(path[2:] if path[:2] in ("a/", "b/") else path)
    return paths


def test_the_patch_folder_holds_no_python_files():
    python_files = [p.relative_to(TRACK).as_posix() for p in PATCHES.rglob("*")
                    if p.is_file() and p.suffix.lower() in (".py", ".pyw", ".pyc")]
    assert python_files == [], "intentional bugs must ship as .patch files only"


def test_there_is_at_least_one_patch():
    assert _patches(), "workshop/advanced/patches/ should hold the Module 6 regression patch"


@pytest.mark.parametrize("patch", _patches(), ids=lambda p: p.name)
def test_each_patch_changes_only_the_reference_inference_file(patch):
    assert _changed_paths(patch.read_text(encoding="utf-8")) == {TARGET}


@pytest.mark.parametrize("patch", _patches(), ids=lambda p: p.name)
def test_each_patch_applies_to_a_copy_of_todays_file(patch, tmp_path):
    git = shutil.which("git")
    assert git, "git is needed to check that the workshop patches still apply"
    copy = tmp_path / TARGET
    copy.parent.mkdir(parents=True)
    shutil.copyfile(ROOT / TARGET, copy)
    before = copy.read_bytes()
    run = subprocess.run([git, "apply", "--check", str(patch)], cwd=tmp_path,
                         capture_output=True, text=True, check=False)
    assert run.returncode == 0, run.stderr
    assert copy.read_bytes() == before  # --check writes nothing; nothing is imported or run


def _imported_top_level_modules(source):
    names = set()
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            names.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            names.add(node.module.split(".")[0])
    return names


def _teaching_scripts():
    return sorted(p for folder in ("solutions", "starter") for p in (TRACK / folder).glob("*.py")
                  if not p.name.startswith("test_"))


def test_there_are_teaching_scripts_to_check():
    assert _teaching_scripts(), "solutions/ and starter/ should hold verify.py"


@pytest.mark.parametrize("script", _teaching_scripts(), ids=lambda p: f"{p.parent.name}/{p.name}")
def test_teaching_scripts_import_only_the_standard_library(script):
    outside = _imported_top_level_modules(script.read_text(encoding="utf-8")) - set(sys.stdlib_module_names)
    assert outside == set(), f"{script.name} imports {sorted(outside)}"


def test_the_loader_uses_the_solutions_by_default(impl_dir, monkeypatch):
    monkeypatch.delenv("RPD_WORKSHOP_IMPL", raising=False)
    assert impl_dir() == TRACK / "solutions"


def test_the_loader_uses_the_starter_when_asked(impl_dir, monkeypatch):
    monkeypatch.setenv("RPD_WORKSHOP_IMPL", "starter")
    assert impl_dir() == TRACK / "starter"


def test_the_loader_refuses_an_unknown_target(impl_dir, monkeypatch):
    monkeypatch.setenv("RPD_WORKSHOP_IMPL", "elsewhere")
    with pytest.raises(ValueError, match="RPD_WORKSHOP_IMPL"):
        impl_dir()
