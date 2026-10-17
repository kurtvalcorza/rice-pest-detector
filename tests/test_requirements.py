"""requirements.txt must list exactly the packages pyproject.toml declares (base + all extras)."""
import re
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _norm(spec: str) -> str:
    return re.sub(r"\s+", "", spec).lower()


def test_requirements_txt_matches_pyproject():
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]
    declared = set(project["dependencies"])
    for extra in project["optional-dependencies"].values():
        declared.update(extra)
    lines = [ln.split("#", 1)[0].strip() for ln in (ROOT / "requirements.txt").read_text(encoding="utf-8").splitlines()]
    listed = {ln for ln in lines if ln and not ln.startswith("-")}
    assert {_norm(s) for s in listed} == {_norm(s) for s in declared}
    assert "-e ." in lines
