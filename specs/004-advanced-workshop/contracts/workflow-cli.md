# Contract: workflow command line (`workflow.py`)

The reference is `workshop/advanced/solutions/workflow.py`; the starter in `workshop/advanced/starter/workflow.py` has the same command line, the transition table as data with gaps marked TODO, and `NotImplementedError` bodies. Standard library only, Python 3.12. Design and alternatives: [research R4](../research.md#r4-the-workflow-state-machine-and-its-history).

## States (7)

| State | Meaning | Terminal |
| :-- | :-- | :-- |
| `planning` | Task created; the agent proposes a plan; a person reads it | no |
| `implementing` | The plan is accepted; the agent is changing code | no |
| `verifying` | The agent says it is done; waiting for a verifier run | no |
| `repairing` | The verifier said FAIL and attempts remain; the agent is fixing | no |
| `awaiting_approval` | The verifier said PASS; waiting for a person | no |
| `approved` | A person approved | yes |
| `blocked` | Stopped: `retry_exhausted`, `verification_unavailable` or `rejected_by_human` | yes |

## Events (8)

| Event | Sent by | How |
| :-- | :-- | :-- |
| `plan_accepted` | human | `event TASK plan_accepted` |
| `implementation_done` | agent (or the learner on its behalf) | `event TASK implementation_done --actor agent` |
| `repair_done` | agent | `event TASK repair_done --actor agent` |
| `verifier_pass`, `verifier_fail`, `verifier_unverified` | verifier | only by `verify TASK`; refused by `event` |
| `approve` | human | `event TASK approve` |
| `reject` | human | `event TASK reject --note "why"` |

## Transition table

Every (state, event) pair not listed is rejected: exit 3, record unchanged. There are 56 pairs in all (7 states × 8 events): 8 are allowed (9 rows below, because `verifier_fail` has two guarded outcomes) and 48 are rejected.

| From | Event | Guard | To | Sets |
| :-- | :-- | :-- | :-- | :-- |
| `planning` | `plan_accepted` | actor is human | `implementing` | |
| `implementing` | `implementation_done` | | `verifying` | |
| `verifying` | `verifier_pass` | | `awaiting_approval` | `attempts += 1` |
| `verifying` | `verifier_fail` | `attempts + 1 < max_attempts` | `repairing` | `attempts += 1` |
| `verifying` | `verifier_fail` | `attempts + 1 == max_attempts` | `blocked` | `attempts += 1`, `blocked_reason = retry_exhausted` |
| `verifying` | `verifier_unverified` | | `blocked` | `attempts += 1`, `blocked_reason = verification_unavailable` |
| `repairing` | `repair_done` | | `verifying` | |
| `awaiting_approval` | `approve` | actor is human | `approved` | |
| `awaiting_approval` | `reject` | actor is human | `blocked` | `blocked_reason = rejected_by_human` |

`verify TASK` maps the stored verify command's exit code: 0 → `verifier_pass`, 1 → `verifier_fail`, anything else (2, other codes, cannot start, killed) → `verifier_unverified`. It is allowed only in `verifying`; in any other state it exits 3 without running the command.

## Commands

```text
python workshop/advanced/solutions/workflow.py --state-dir DIR start TASK [--max-attempts N] -- VERIFY_COMMAND [ARG ...]
python workshop/advanced/solutions/workflow.py --state-dir DIR event TASK EVENT [--actor human|agent] [--note TEXT]
python workshop/advanced/solutions/workflow.py --state-dir DIR verify TASK
python workshop/advanced/solutions/workflow.py --state-dir DIR show TASK
```

- `start` creates `DIR/TASK.json` in `planning` with an empty history. `--max-attempts` is 1–3 (default 3). Fails with exit 4 if the record already exists.
- `event` applies one event; `--actor` defaults to `human`.
- `verify` runs the stored command (normally a `verify.py` call), records the result and prints the new state.
- `show` prints the state, attempts, last verification and the history as a table; changes nothing.

Every command that changes a record writes it to `DIR/TASK.json.tmp` and then replaces `DIR/TASK.json` (`os.replace`), so the file is always either the old or the new record.

## Exit codes

| Code | Meaning |
| :-- | :-- |
| 0 | Done: the event was applied (whatever the new state, including `blocked`), or `show` printed |
| 2 | Usage error (unknown command or option, bad task ID, `--max-attempts` out of range) |
| 3 | Invalid transition: the event is not allowed in this state, the actor is wrong, or a `verifier_*` event was sent by hand. Record unchanged |
| 4 | Record problem: missing (for `event`, `verify`, `show`), already exists (for `start`), unreadable, or failing an invariant from the [data model](../data-model.md#workflow-record-task-idjson) |

## Record format

See [data-model.md](../data-model.md#workflow-record-task-idjson). Example after a success run with one repair:

```json
{
  "schema": 1,
  "task_id": "m7-success",
  "state": "approved",
  "attempts": 2,
  "max_attempts": 3,
  "verify_command": ["python", "workshop/advanced/solutions/verify.py", "--min-tests", "4", "--", "uv", "run", "...", "--junitxml={junit}"],
  "last_verification": {"exit_code": 0, "result": "PASS", "reason": "4 tests ran, 0 failed", "evidence": null},
  "blocked_reason": null,
  "created_at": "2026-10-26T09:00:00Z",
  "updated_at": "2026-10-26T09:20:00Z",
  "history": [
    {"seq": 1, "at": "2026-10-26T09:02:00Z", "actor": "human", "event": "plan_accepted", "from": "planning", "to": "implementing", "attempt": null, "verification": null, "note": null},
    {"seq": 2, "at": "2026-10-26T09:06:00Z", "actor": "agent", "event": "implementation_done", "from": "implementing", "to": "verifying", "attempt": null, "verification": null, "note": null},
    {"seq": 3, "at": "2026-10-26T09:07:00Z", "actor": "verifier", "event": "verifier_fail", "from": "verifying", "to": "repairing", "attempt": 1, "verification": {"exit_code": 1, "result": "FAIL", "reason": "1 of 4 tests failed"}, "note": null},
    {"seq": 4, "at": "2026-10-26T09:12:00Z", "actor": "agent", "event": "repair_done", "from": "repairing", "to": "verifying", "attempt": null, "verification": null, "note": null},
    {"seq": 5, "at": "2026-10-26T09:13:00Z", "actor": "verifier", "event": "verifier_pass", "from": "verifying", "to": "awaiting_approval", "attempt": 2, "verification": {"exit_code": 0, "result": "PASS", "reason": "4 tests ran, 0 failed"}, "note": null},
    {"seq": 6, "at": "2026-10-26T09:20:00Z", "actor": "human", "event": "approve", "from": "awaiting_approval", "to": "approved", "attempt": null, "verification": null, "note": "diff read; only infer.py restored"}
  ]
}
```

## What this does not protect

Stated in Module 7's page: the record is a local file the agent could edit, and `--actor human` is not authenticated. The workflow makes the process visible and bounded; it does not stop a tool with write access from lying. Module 8 moves the approval to a pull-request review, which the agent cannot give itself.
