"""Load the advanced track's scripts by file path: the reference solutions, or the learner's starter.

CI runs these tests against ``workshop/advanced/solutions/``. A learner points the same tests at
``workshop/advanced/starter/`` by setting ``RPD_WORKSHOP_IMPL=starter``; they fail with
``NotImplementedError`` until the starter is filled in. Loading by path keeps a generic module name
such as ``verify`` off ``sys.path``.
"""

import importlib.util
import os
import sys
from pathlib import Path

import pytest

TRACK = Path(__file__).resolve().parents[1]
TARGETS = {"solutions": TRACK / "solutions", "starter": TRACK / "starter"}


def _impl_dir():
    name = os.environ.get("RPD_WORKSHOP_IMPL", "").strip().lower() or "solutions"
    if name not in TARGETS:
        raise ValueError(f"RPD_WORKSHOP_IMPL must be 'solutions' or 'starter', not {name!r}")
    return TARGETS[name]


def _load(stem):
    path = _impl_dir() / f"{stem}.py"
    module_name = f"rpd_workshop_{path.parent.name}_{stem}"
    spec = importlib.util.spec_from_file_location(module_name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module  # dataclasses look their module up while the class is built
    try:
        spec.loader.exec_module(module)
    except BaseException:
        sys.modules.pop(module_name, None)
        raise
    return module


@pytest.fixture
def impl_dir():
    """The folder the tests load from, as a function so a test can change the variable first."""
    return _impl_dir


@pytest.fixture
def verify_path():
    return _impl_dir() / "verify.py"


@pytest.fixture
def verify_mod():
    return _load("verify")


@pytest.fixture
def workflow_mod():
    return _load("workflow")
