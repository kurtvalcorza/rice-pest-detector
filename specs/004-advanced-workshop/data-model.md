# Data Model: Advanced Workshop Track

**Feature**: [spec.md](spec.md) | **Plan**: [plan.md](plan.md)

Four kinds of record, all plain files a learner can open in an editor. None is read by the detector or the app. Times are UTC in ISO 8601 with a `Z` suffix (for example `2026-10-26T09:15:02Z`). Paths are written relative to the folder the learner passed in, never absolute, so a bundle can be shared without exposing a home folder.

## Verifier result (`verification.json`)

Written by `verify.py` to its evidence folder on every run, including UNVERIFIED runs.

| Field | Type | Rule |
| :-- | :-- | :-- |
| `result` | string | `PASS`, `FAIL` or `UNVERIFIED` |
| `exit_code` | int | 0, 1 or 2; always matches `result` |
| `reason` | string | One sentence, from the decision table in [contracts/verifier-cli.md](contracts/verifier-cli.md) (for example "3 tests ran, fewer than the 4 required") |
| `command` | list of strings | The command as run, with `{junit}` replaced |
| `command_exit_code` | int or null | The command's own exit code; null if it never started or timed out |
| `report` | object or null | Counts read from the JUnit report (below); null if there was no readable report |
| `min_tests` | int | The required number of tests (default 1) |
| `started_at`, `finished_at` | string | Times |
| `duration_seconds` | number | Wall-clock time of the command |
| `log` | string | `run.log`: the command's standard output and error |
| `junit` | string | `junit.xml`, the report path inside the evidence folder |

**Report counts** (`report`): `tests`, `failures`, `errors`, `skipped` (ints, summed over every `<testsuite>`), and `failed_tests` (list of `classname::name` for each failure or error, at most 20).

**Rules**: `result` is `PASS` only when `command_exit_code` is 0, `report` is not null, `report.tests >= min_tests`, `report.failures + report.errors == 0` and `report.tests > report.skipped`. A report file that existed before the run is deleted first; if the command does not write a new one, `report` is null.

## Workflow record (`<task-id>.json`)

One file per task in the state folder given to `workflow.py` (`--state-dir`).

| Field | Type | Rule |
| :-- | :-- | :-- |
| `schema` | int | `1` |
| `task_id` | string | Matches `^[a-z0-9][a-z0-9-]{0,39}$` (also the file name; no path separators) |
| `state` | string | One of the 7 states in [contracts/workflow-cli.md](contracts/workflow-cli.md) |
| `attempts` | int | Verification attempts used, 0–`max_attempts` |
| `max_attempts` | int | 1–3; default 3 |
| `verify_command` | list of strings | The verifier command run by `workflow.py verify`, stored at `start` |
| `last_verification` | object or null | `{exit_code, result, reason, evidence}` from the last verifier run; `evidence` is the verifier's evidence folder if the command named one |
| `blocked_reason` | string or null | `retry_exhausted`, `verification_unavailable` or `rejected_by_human` when `state` is `blocked`; otherwise null |
| `created_at`, `updated_at` | string | Times |
| `history` | list of transition | Append-only, in order (below) |

**State lifecycle**: `planning` → `implementing` → `verifying` → (`repairing` → `verifying`)* → `awaiting_approval` → `approved`; any of `verifying` or `awaiting_approval` can end in `blocked`. `approved` and `blocked` are terminal.

**Invariants** (each has a test): `state` equals the `to` of the last history entry (or `planning` with an empty history); `attempts` equals the number of `verifier_*` entries; `seq` runs 1, 2, 3… with no gaps; earlier entries never change; `approve` and `reject` entries have actor `human`; `verifier_*` entries have actor `verifier`.

## Transition (one entry in `history`)

| Field | Type | Rule |
| :-- | :-- | :-- |
| `seq` | int | 1 for the first transition, then +1 |
| `at` | string | Time |
| `actor` | string | `human`, `agent` or `verifier` |
| `event` | string | One of the 8 events |
| `from`, `to` | string | States; must be a row of the transition table |
| `attempt` | int or null | The attempt number for `verifier_*` events; else null |
| `verification` | object or null | For `verifier_*` events: `{exit_code, result, reason}` |
| `note` | string or null | Free text from `--note`, at most 500 characters |

A rejected event (not in the table) writes nothing: the file is byte-for-byte unchanged.

## Evidence bundle (per module)

A folder the learner keeps, outside the clone and any worktree: `agents-practice/advanced-evidence/<m6|m7|m8>/`. Contents are listed, with the check for each, in [contracts/evidence-checklist.md](contracts/evidence-checklist.md).

| Item | Module | Source |
| :-- | :-- | :-- |
| `baseline/`, `regression/`, `restored/`, `unavailable/` | 6 | One verifier evidence folder per run (`verification.json`, `run.log`, `junit.xml`) |
| `regression.diff` | 6 | `git diff` in the worktree after applying the patch |
| `stop-hook.txt` | 6 | Output of running the Stop hook by hand in the patched worktree |
| `records/<task-id>.json` | 7 | The workflow records for the success and the exhaustion runs |
| `prompts.md` | 7 | The prompts handed to the agent at each handoff |
| `links.md` | 8 | Issue, pull request and CI run URLs in the learner's fork |
| `review.md` | 8 | The learner's review notes on the pull request |
| `reflection.md` | 6, 7, 8 | Answers to each module's reflection questions |

**Rule**: nothing in a bundle may contain a token, key, password or personal data; the checklist's last item for each module is to check this before sharing.
