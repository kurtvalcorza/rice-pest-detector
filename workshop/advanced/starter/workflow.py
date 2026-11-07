"""STARTER: a bounded agent loop. Fill in the TODOs, test-first.

Point the track's tests at this file and watch them fail, then make them pass one at a time:

    RPD_WORKSHOP_IMPL=starter python -m pytest workshop/advanced/tests        # macOS, Linux
    $env:RPD_WORKSHOP_IMPL="starter"; python -m pytest workshop/advanced/tests  # Windows PowerShell

Usage, once finished (the same as the reference in ``workshop/advanced/solutions/workflow.py``):
    python workflow.py --state-dir DIR start TASK [--max-attempts N] -- VERIFY_COMMAND [ARG ...]
    python workflow.py --state-dir DIR event TASK EVENT [--actor human|agent] [--note TEXT]
    python workflow.py --state-dir DIR verify TASK
    python workflow.py --state-dir DIR show TASK

Only the verifier's exit code moves a task out of ``verifying``, a task gets at most three attempts,
and only a person approves. Exit codes: 0 done, 2 usage error, 3 invalid transition, 4 record problem.
The tables are in specs/004-advanced-workshop/contracts/workflow-cli.md. Standard library only.
"""

import os  # noqa: F401 - save_record needs os.replace
import sys
from typing import NamedTuple

STATES = ("planning", "implementing", "verifying", "repairing", "awaiting_approval", "approved", "blocked")
EVENTS = ("plan_accepted", "implementation_done", "repair_done", "verifier_pass", "verifier_fail",
          "verifier_unverified", "approve", "reject")
TERMINAL = ("approved", "blocked")
VERIFIER_EVENTS = {"verifier_pass": "PASS", "verifier_fail": "FAIL", "verifier_unverified": "UNVERIFIED"}
MAX_ATTEMPTS = 3
MAX_NOTE = 500
SCHEMA = 1


class Row(NamedTuple):
    source: str
    event: str
    guard: str | None  # None, "human", "attempts_left" or "last_attempt"
    target: str
    blocked_reason: str | None = None


# The whole workflow, as data. Any (state, event) pair not listed here is rejected.
TRANSITIONS = (
    Row("planning", "plan_accepted", "human", "implementing"),
    Row("implementing", "implementation_done", None, "verifying"),
    Row("verifying", "verifier_pass", None, "awaiting_approval"),
    # TODO: verifier_fail while attempts remain.
    # TODO: verifier_fail on the last attempt. Which blocked_reason?
    # TODO: verifier_unverified. Why is this one never worth a repair?
    Row("repairing", "repair_done", None, "verifying"),
    # TODO: approve. Who may send it?
    Row("awaiting_approval", "reject", "human", "blocked", "rejected_by_human"),
)


class UsageError(Exception):
    """Exit 2: invalid arguments."""


class InvalidTransition(Exception):
    """Exit 3: the table does not allow this event now. The record stays as it is."""


class RecordError(Exception):
    """Exit 4: the record is missing, already exists, is unreadable or breaks an invariant."""


def find_row(state, event, actor, attempts, max_attempts):
    """Return the row of TRANSITIONS this event takes, or raise InvalidTransition with the reason.

    ``verifier_*`` events need actor ``verifier`` and no other event may have it. A row's guard must
    hold: "human" means actor is human; "attempts_left" means attempts + 1 < max_attempts;
    "last_attempt" means attempts + 1 == max_attempts.
    """
    # TODO: a list of matching rows, then the first whose guard holds.
    raise NotImplementedError("find_row: TODO")


def new_record(task_id, verify_command, max_attempts=MAX_ATTEMPTS, now=None):
    """Return a record in ``planning`` with an empty history, with the fields in data-model.md."""
    # TODO: schema, task_id, state, attempts, max_attempts, verify_command, last_verification,
    # blocked_reason, created_at, updated_at, history. Times are UTC, like 2026-10-26T09:15:02Z.
    raise NotImplementedError("new_record: TODO")


def apply_event(record, event, actor, note=None, verification=None, evidence=None, now=None):
    """Return a NEW record with this event applied; the given record must not change.

    Appends one history entry (seq, at, actor, event, from, to, attempt, verification, note), sets
    state and blocked_reason from the row. A verifier event also adds 1 to attempts and sets
    last_verification to the verification plus ``evidence``.
    """
    # TODO: find_row first, so a rejected event raises before anything is touched. copy.deepcopy helps.
    raise NotImplementedError("apply_event: TODO")


def validate_record(record):
    """Raise RecordError unless the record keeps every invariant in data-model.md.

    Replay the history through the table from ``planning``: seq has no gaps, each entry follows from
    the one before, and state, attempts, blocked_reason and last_verification match where it ends.
    """
    # TODO: fields and types first, then the replay. A broken record must not raise anything else.
    raise NotImplementedError("validate_record: TODO")


def valid_task_id(task_id):
    """True when the ID matches ``^[a-z0-9][a-z0-9-]{0,39}$``, which keeps it a safe file name."""
    # TODO: re.fullmatch, because `$` also matches before a final newline.
    raise NotImplementedError("valid_task_id: TODO")


def record_path(state_dir, task_id):
    """Return the path ``state_dir/task_id.json``."""
    raise NotImplementedError("record_path: TODO")


def load_record(state_dir, task_id):
    """Return the checked record. RecordError if missing, unreadable, invalid or filed under another ID."""
    raise NotImplementedError("load_record: TODO")


def save_record(state_dir, record):
    """Write to ``TASK.json.tmp``, then ``os.replace`` it onto ``TASK.json``. RecordError if that fails.

    A failed write must leave the old file as it was and no ``.tmp`` behind.
    """
    raise NotImplementedError("save_record: TODO")


def event_for_exit(exit_code):
    """Return verifier_pass for 0, verifier_fail for 1, verifier_unverified for anything else."""
    raise NotImplementedError("event_for_exit: TODO")


def run_verifier(command):
    """Run the stored command without a shell; return (exit code or None, output, why it did not start)."""
    # TODO: shutil.which, subprocess.run. A command that cannot start must not crash the workflow.
    raise NotImplementedError("run_verifier: TODO")


def main(argv=None):
    """Parse the arguments, run start, event, verify or show, and return the exit code.

    ``verify`` is allowed only in ``verifying`` and must not run the command anywhere else. ``event``
    refuses ``verifier_*`` events. ``show`` prints the state, attempts, last verification and history.
    """
    # TODO: argparse with sub-commands; everything after the first "--" is the verify command.
    raise NotImplementedError("main: TODO")


if __name__ == "__main__":
    sys.exit(main())
