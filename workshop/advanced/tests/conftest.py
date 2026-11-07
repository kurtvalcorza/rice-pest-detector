"""Load the advanced track's scripts by file path: the reference solutions, or the learner's starter.

CI runs these tests against ``workshop/advanced/solutions/``. A learner points the same tests at
``workshop/advanced/starter/`` by setting ``RPD_WORKSHOP_IMPL=starter``; they fail with
``NotImplementedError`` until the starter is filled in. Loading by path keeps a generic module name
such as ``verify`` off ``sys.path``.
"""

import importlib.util
import os
import subprocess
import sys
from pathlib import Path

import pytest

TRACK = Path(__file__).resolve().parents[1]
TARGETS = {"solutions": TRACK / "solutions", "starter": TRACK / "starter"}

# Who sends each workflow event in the tests, what a verifier run reports, and how to reach each state.
ACTORS = {"plan_accepted": "human", "implementation_done": "agent", "repair_done": "agent", "approve": "human",
          "reject": "human", "verifier_pass": "verifier", "verifier_fail": "verifier",
          "verifier_unverified": "verifier"}
VERIFICATIONS = {"verifier_pass": {"exit_code": 0, "result": "PASS", "reason": "4 tests ran, 0 failed"},
                 "verifier_fail": {"exit_code": 1, "result": "FAIL", "reason": "1 of 4 tests failed: t::x"},
                 "verifier_unverified": {"exit_code": 2, "result": "UNVERIFIED", "reason": "command not found: uv"}}
TO_VERIFYING = ("plan_accepted", "implementation_done")
ROUTES = {"planning": (), "implementing": ("plan_accepted",), "verifying": TO_VERIFYING,
          "repairing": (*TO_VERIFYING, "verifier_fail"), "awaiting_approval": (*TO_VERIFYING, "verifier_pass"),
          "approved": (*TO_VERIFYING, "verifier_pass", "approve"),
          "blocked": (*TO_VERIFYING, "verifier_pass", "reject")}


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


@pytest.fixture
def workflow_path():
    return _impl_dir() / "workflow.py"


@pytest.fixture
def mutation_check_mod():
    return _load("mutation_check")


@pytest.fixture
def mutation_check_path():
    return _impl_dir() / "mutation_check.py"


@pytest.fixture
def send(workflow_mod):
    """Apply events in order, each from its usual actor, and return the new record."""
    def apply(record, *events):
        for event in events:
            record = workflow_mod.apply_event(record, event, ACTORS[event], verification=VERIFICATIONS.get(event))
        return record
    return apply


@pytest.fixture
def reach(workflow_mod, send):
    """A record that really travelled to the given state, through the table."""
    def make(state, max_attempts=3):
        return send(workflow_mod.new_record("t1", ["verify"], max_attempts), *ROUTES[state])
    return make


@pytest.fixture
def cli(workflow_path, tmp_path):
    """Run workflow.py as a learner would, with a state folder under tmp_path."""
    def run(*args):
        return subprocess.run([sys.executable, str(workflow_path), "--state-dir", str(run.state_dir), *args],
                              cwd=tmp_path, capture_output=True, text=True, encoding="utf-8", errors="replace",
                              timeout=120, check=False)
    run.state_dir = tmp_path / "state"
    return run
