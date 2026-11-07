"""A bounded agent loop: a state machine where only the verifier's exit code moves a task forward.

Usage:
    python workflow.py --state-dir DIR start TASK [--max-attempts N] -- VERIFY_COMMAND [ARG ...]
    python workflow.py --state-dir DIR event TASK EVENT [--actor human|agent] [--note TEXT]
    python workflow.py --state-dir DIR verify TASK
    python workflow.py --state-dir DIR show TASK

The agent can say it is done, which only moves the task to ``verifying``. ``verify`` runs the stored
command and maps its exit code to an event: 0 is ``verifier_pass``, 1 is ``verifier_fail``, anything
else is ``verifier_unverified``. Those three events cannot be sent by hand, a task gets at most three
verification attempts, and only a person may approve or reject. The contract is
``specs/004-advanced-workshop/contracts/workflow-cli.md``.

Exit codes: 0 done, 2 usage error, 3 invalid transition (record unchanged), 4 record problem. A task
ending ``blocked`` is still exit 0: the event was applied.

The record is a local file and ``--actor human`` is not authenticated: this makes the process visible
and bounded, it does not stop a tool with write access from lying. Standard library only.
"""

import argparse
import copy
import json
import os
import re
import shutil
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import NamedTuple

STATES = ("planning", "implementing", "verifying", "repairing", "awaiting_approval", "approved", "blocked")
EVENTS = ("plan_accepted", "implementation_done", "repair_done", "verifier_pass", "verifier_fail",
          "verifier_unverified", "approve", "reject")
TERMINAL = ("approved", "blocked")
VERIFIER_EVENTS = {"verifier_pass": "PASS", "verifier_fail": "FAIL", "verifier_unverified": "UNVERIFIED"}
MAX_ATTEMPTS = 3
MAX_NOTE = 500
SCHEMA = 1

TASK_ID = re.compile(r"[a-z0-9][a-z0-9-]{0,39}")
TIME = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z")
RESULT_LINE = re.compile(r"^RESULT: (PASS|FAIL|UNVERIFIED) \((.*)\) evidence=", re.MULTILINE)

RECORD_FIELDS = {"schema", "task_id", "state", "attempts", "max_attempts", "verify_command", "last_verification",
                 "blocked_reason", "created_at", "updated_at", "history"}
ENTRY_FIELDS = {"seq", "at", "actor", "event", "from", "to", "attempt", "verification", "note"}


class Row(NamedTuple):
    source: str
    event: str
    guard: str | None
    target: str
    blocked_reason: str | None = None


# The whole workflow, as data. Any (state, event) pair not listed here is rejected.
TRANSITIONS = (
    Row("planning", "plan_accepted", "human", "implementing"),
    Row("implementing", "implementation_done", None, "verifying"),
    Row("verifying", "verifier_pass", None, "awaiting_approval"),
    Row("verifying", "verifier_fail", "attempts_left", "repairing"),
    Row("verifying", "verifier_fail", "last_attempt", "blocked", "retry_exhausted"),
    Row("verifying", "verifier_unverified", None, "blocked", "verification_unavailable"),
    Row("repairing", "repair_done", None, "verifying"),
    Row("awaiting_approval", "approve", "human", "approved"),
    Row("awaiting_approval", "reject", "human", "blocked", "rejected_by_human"),
)


class UsageError(Exception):
    """Exit 2: invalid arguments."""


class InvalidTransition(Exception):
    """Exit 3: the table does not allow this event now. The record stays as it is."""


class RecordError(Exception):
    """Exit 4: the record is missing, already exists, is unreadable or breaks an invariant."""


def _now():
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _guard_holds(guard, actor, attempts, max_attempts):
    return {None: True, "human": actor == "human", "attempts_left": attempts + 1 < max_attempts,
            "last_attempt": attempts + 1 == max_attempts}[guard]


def find_row(state, event, actor, attempts, max_attempts):
    """The row of the table this event takes, or InvalidTransition with the reason."""
    if (event in VERIFIER_EVENTS) != (actor == "verifier"):
        raise InvalidTransition(f"{event} cannot come from actor {actor}: "
                                "only a verifier run records a verifier result")
    rows = [row for row in TRANSITIONS if (row.source, row.event) == (state, event)]
    if not rows:
        allowed = sorted({row.event for row in TRANSITIONS if row.source == state}) or ["nothing: it is finished"]
        raise InvalidTransition(f"{event} is not allowed in {state}; allowed here: {', '.join(allowed)}")
    for row in rows:
        if _guard_holds(row.guard, actor, attempts, max_attempts):
            return row
    raise InvalidTransition(f"{event} in {state} needs a person, not actor {actor}")


def new_record(task_id, verify_command, max_attempts=MAX_ATTEMPTS, now=None):
    at = now or _now()
    return {"schema": SCHEMA, "task_id": task_id, "state": "planning", "attempts": 0, "max_attempts": max_attempts,
            "verify_command": list(verify_command), "last_verification": None, "blocked_reason": None,
            "created_at": at, "updated_at": at, "history": []}


def apply_event(record, event, actor, note=None, verification=None, evidence=None, now=None):
    """Return a new record with this event applied; the given record is not changed."""
    row = find_row(record["state"], event, actor, record["attempts"], record["max_attempts"])
    after, at = copy.deepcopy(record), now or _now()
    is_verifier = event in VERIFIER_EVENTS
    if is_verifier:
        after["attempts"] += 1
        after["last_verification"] = {**verification, "evidence": evidence}
    after["state"], after["blocked_reason"], after["updated_at"] = row.target, row.blocked_reason, at
    after["history"].append({"seq": len(record["history"]) + 1, "at": at, "actor": actor, "event": event,
                             "from": row.source, "to": row.target,
                             "attempt": after["attempts"] if is_verifier else None,
                             "verification": dict(verification) if is_verifier else None, "note": note})
    return after


def _is_int(value):
    return type(value) is int  # bool is an int to isinstance, not to a record


def _is_time(value):
    return isinstance(value, str) and TIME.fullmatch(value) is not None


def _entry_problem(entry, seq, state, attempts, max_attempts):
    """What is wrong with one history entry, replayed through the table from the state before it."""
    if set(entry) != ENTRY_FIELDS:
        return f"entry {seq} does not have the transition fields"
    if entry["seq"] != seq:
        return f"entry {seq} has seq {entry['seq']}"
    if not _is_time(entry["at"]):
        return f"entry {seq} has a bad time"
    if entry["event"] not in EVENTS or entry["actor"] not in ("human", "agent", "verifier"):
        return f"entry {seq} has an unknown event or actor"
    if entry["from"] != state:
        return f"entry {seq} starts from {entry['from']}, but the task was in {state}"
    try:
        row = find_row(state, entry["event"], entry["actor"], attempts, max_attempts)
    except InvalidTransition as exc:
        return f"entry {seq}: {exc}"
    if entry["to"] != row.target:
        return f"entry {seq} goes to {entry['to']}, but the table says {row.target}"
    if entry["note"] is not None and (not isinstance(entry["note"], str) or len(entry["note"]) > MAX_NOTE):
        return f"entry {seq} has a bad note"
    if entry["event"] not in VERIFIER_EVENTS:
        return None if entry["attempt"] is None and entry["verification"] is None else (
            f"entry {seq} holds a verifier result but is not a verifier event")
    verification = entry["verification"]
    if entry["attempt"] != attempts + 1:
        return f"entry {seq} has attempt {entry['attempt']}, expected {attempts + 1}"
    if not isinstance(verification, dict) or set(verification) != {"exit_code", "result", "reason"}:
        return f"entry {seq} has no verification result"
    if verification["result"] != VERIFIER_EVENTS[entry["event"]]:
        return f"entry {seq}: result {verification['result']} does not match {entry['event']}"
    return None


def _record_problem(record):
    """The first invariant from the data model this record breaks, or None."""
    if not isinstance(record, dict) or set(record) != RECORD_FIELDS:
        return "the record does not have the expected fields"
    if record["schema"] != SCHEMA:
        return f"schema is {record['schema']}, expected {SCHEMA}"
    if not valid_task_id(record["task_id"]):
        return "the task ID is not valid"
    if record["state"] not in STATES:
        return f"unknown state {record['state']}"
    if not _is_int(record["max_attempts"]) or not 1 <= record["max_attempts"] <= MAX_ATTEMPTS:
        return "max_attempts is not 1 to 3"
    if not _is_int(record["attempts"]) or not 0 <= record["attempts"] <= record["max_attempts"]:
        return "attempts is not between 0 and max_attempts"
    command = record["verify_command"]
    if not isinstance(command, list) or not command or not all(isinstance(arg, str) for arg in command):
        return "verify_command is not a list of strings"
    if not _is_time(record["created_at"]) or not _is_time(record["updated_at"]):
        return "a time is not UTC ISO 8601 with a Z"
    if not isinstance(record["history"], list):
        return "history is not a list"

    state, attempts, blocked_reason, last = "planning", 0, None, None
    for seq, entry in enumerate(record["history"], start=1):
        problem = _entry_problem(entry, seq, state, attempts, record["max_attempts"])
        if problem:
            return problem
        row = find_row(state, entry["event"], entry["actor"], attempts, record["max_attempts"])
        state, blocked_reason = row.target, row.blocked_reason
        if entry["event"] in VERIFIER_EVENTS:
            attempts, last = attempts + 1, entry["verification"]
    if record["state"] != state:
        return f"state is {record['state']}, but the history ends in {state}"
    if record["attempts"] != attempts:
        return f"attempts is {record['attempts']}, but the history holds {attempts} verifier runs"
    if record["blocked_reason"] != blocked_reason:
        return f"blocked_reason is {record['blocked_reason']}, but the history says {blocked_reason}"
    kept = record["last_verification"]
    if (kept and {key: kept.get(key) for key in ("exit_code", "result", "reason")}) != (last and dict(last)):
        return "last_verification does not match the last verifier entry"
    return None


def validate_record(record):
    """Raise RecordError unless the record keeps every invariant in the data model."""
    try:
        problem = _record_problem(record)
    except (KeyError, TypeError, AttributeError, IndexError) as exc:
        problem = f"malformed record ({type(exc).__name__}: {exc})"
    if problem:
        raise RecordError(problem)


def valid_task_id(task_id):
    return isinstance(task_id, str) and TASK_ID.fullmatch(task_id) is not None


def record_path(state_dir, task_id):
    return Path(state_dir) / f"{task_id}.json"


def load_record(state_dir, task_id):
    """The checked record for this task; RecordError if it is missing, unreadable or invalid."""
    path = record_path(state_dir, task_id)
    try:
        record = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise RecordError(f"no record for {task_id} at {path}") from None
    except (OSError, ValueError) as exc:  # ValueError covers bad JSON and undecodable bytes
        raise RecordError(f"cannot read {path}: {exc}") from None
    validate_record(record)
    if record["task_id"] != task_id:
        raise RecordError(f"{path} holds the record of {record['task_id']}")
    return record


def save_record(state_dir, record):
    """Write to TASK.json.tmp, then replace: the file is always the old or the new record, never half."""
    path = record_path(state_dir, record["task_id"])
    temporary = path.with_name(path.name + ".tmp")
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8", newline="\n")
        os.replace(temporary, path)
    except OSError as exc:
        temporary.unlink(missing_ok=True)
        raise RecordError(f"cannot write {path}: {exc}") from None


def event_for_exit(exit_code):
    """0 is a pass, 1 a failure worth repairing; anything else, or no code at all, is unverified."""
    return {0: "verifier_pass", 1: "verifier_fail"}.get(exit_code, "verifier_unverified")


def run_verifier(command):
    """Run the stored command without a shell; return (exit code or None, output, why it did not start)."""
    program = shutil.which(command[0])
    if program is None:
        return None, "", f"command not found: {command[0]}"
    try:
        done = subprocess.run([program, *command[1:]], stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                              stderr=subprocess.STDOUT, check=False)
    except OSError as exc:
        return None, "", f"the command could not start: {exc.strerror or exc}"
    return done.returncode, done.stdout.decode("utf-8", errors="replace"), None


def verification_from(exit_code, output, detail):
    """The {exit_code, result, reason} to record. The exit code decides; the text only explains."""
    result = VERIFIER_EVENTS[event_for_exit(exit_code)]
    reason = detail or f"the command exited {exit_code}"
    lines = RESULT_LINE.findall(output)
    if lines and lines[-1][0] == result:
        reason = lines[-1][1]
    return {"exit_code": exit_code, "result": result, "reason": reason}


def evidence_folder(command):
    """The folder named by ``--evidence`` in a verify.py call, as the learner wrote it; else None."""
    options = command[:command.index("--")] if "--" in command else command
    for position, arg in enumerate(options):
        if arg == "--evidence" and position + 1 < len(options):
            return options[position + 1]
        if arg.startswith("--evidence="):
            return arg.split("=", 1)[1]
    return None


def _start(args, command):
    if not command:
        raise UsageError("start needs a verify command after --")
    if not 1 <= args.max_attempts <= MAX_ATTEMPTS:
        raise UsageError(f"--max-attempts must be 1 to {MAX_ATTEMPTS}")
    if record_path(args.state_dir, args.task).exists():
        raise RecordError(f"a record for {args.task} already exists")
    save_record(args.state_dir, new_record(args.task, command, args.max_attempts))
    print(f"{args.task}: planning")


def _event(args, _):
    if args.note is not None and len(args.note) > MAX_NOTE:
        raise UsageError(f"--note is limited to {MAX_NOTE} characters")
    record = load_record(args.state_dir, args.task)
    if args.event in VERIFIER_EVENTS:
        raise InvalidTransition(f"{args.event} cannot be sent by hand: run `workflow.py verify {args.task}`")
    after = apply_event(record, args.event, args.actor, note=args.note)
    save_record(args.state_dir, after)
    print(f"{args.task}: {record['state']} -> {after['state']} ({args.event}, actor {args.actor})")


def _verify(args, _):
    record = load_record(args.state_dir, args.task)
    if record["state"] != "verifying":
        raise InvalidTransition(f"verify is allowed only in verifying, and {args.task} is in {record['state']}")
    exit_code, output, detail = run_verifier(record["verify_command"])
    verification = verification_from(exit_code, output, detail)
    after = apply_event(record, event_for_exit(exit_code), "verifier", verification=verification,
                        evidence=evidence_folder(record["verify_command"]))
    save_record(args.state_dir, after)
    lines = [line for line in output.splitlines() if line.startswith("RESULT: ")]
    print(lines[-1] if lines else f"RESULT: {verification['result']} ({verification['reason']})")
    print(f"{args.task}: verifying -> {after['state']} (attempt {after['attempts']} of {after['max_attempts']})")


def _table(rows):
    widths = [max(len(row[column]) for row in rows) for column in range(len(rows[0]))]
    return ["  ".join(cell.ljust(width) for cell, width in zip(row, widths, strict=True)).rstrip() for row in rows]


def _show(args, _):
    record = load_record(args.state_dir, args.task)
    last = record["last_verification"]
    print(f"task:     {record['task_id']}")
    print(f"state:    {record['state']}" + (f" ({record['blocked_reason']})" if record["blocked_reason"] else ""))
    print(f"attempts: {record['attempts']} of {record['max_attempts']}")
    print(f"last verification: {last['result']}, exit {last['exit_code']}: {last['reason']}" if last
          else "last verification: none")
    rows = [("seq", "at", "actor", "event", "from", "to", "attempt", "result", "note")]
    for entry in record["history"]:
        rows.append((str(entry["seq"]), entry["at"], entry["actor"], entry["event"], entry["from"], entry["to"],
                     "" if entry["attempt"] is None else str(entry["attempt"]),
                     entry["verification"]["result"] if entry["verification"] else "", entry["note"] or ""))
    print()
    print("\n".join(_table(rows)))


class _Parser(argparse.ArgumentParser):
    def error(self, message):
        raise UsageError(message)


def _parse(argv):
    """Split at the first ``--``: what follows is the verify command, left exactly as given."""
    if "--" in argv:
        split = argv.index("--")
        options, command = argv[:split], argv[split + 1:]
    else:
        options, command = argv, []
    parser = _Parser(prog="workflow.py", description=__doc__.splitlines()[0])
    parser.add_argument("--state-dir", type=Path, required=True)
    commands = parser.add_subparsers(dest="command", required=True)
    start = commands.add_parser("start")
    start.add_argument("task")
    start.add_argument("--max-attempts", type=int, default=MAX_ATTEMPTS)
    start.set_defaults(handler=_start)
    event = commands.add_parser("event")
    event.add_argument("task")
    event.add_argument("event", choices=EVENTS)
    event.add_argument("--actor", choices=("human", "agent"), default="human")
    event.add_argument("--note")
    event.set_defaults(handler=_event)
    for name, handler in (("verify", _verify), ("show", _show)):
        sub = commands.add_parser(name)
        sub.add_argument("task")
        sub.set_defaults(handler=handler)
    args = parser.parse_args(options)
    if args.command != "start" and command:
        raise UsageError(f"{args.command} takes nothing after --")
    if not valid_task_id(args.task):
        raise UsageError(f"bad task ID {args.task!r}: use lower-case letters, digits and hyphens, at most 40")
    return args, command


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    try:
        args, command = _parse(argv)
        args.handler(args, command)
        return 0
    except UsageError as exc:
        print(f"usage error: {exc}", file=sys.stderr)
        return 2
    except InvalidTransition as exc:
        print(f"refused: {exc}", file=sys.stderr)
        return 3
    except RecordError as exc:
        print(f"record problem: {exc}", file=sys.stderr)
        return 4


if __name__ == "__main__":
    sys.exit(main())
