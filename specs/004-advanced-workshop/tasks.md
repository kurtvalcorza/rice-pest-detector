---
description: "Task list for the advanced workshop track"
---

# Tasks: Advanced Workshop Track

**Input**: Design documents from `/specs/004-advanced-workshop/`

**Prerequisites**: [plan.md](plan.md), [spec.md](spec.md), [research.md](research.md), [data-model.md](data-model.md), [contracts/](contracts/), [quickstart.md](quickstart.md)

**Tests**: Required. Constitution Principle III (test-first) is non-negotiable: every test task below is written first and must fail for the right reason before its implementation task starts.

**Organization**: Tasks are grouped by user story so each module can be built, tested and tried on its own. Nothing starts until the owner has reviewed issue #3 and confirmed research R1 (T001).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependency on an unfinished task)
- **[Story]**: The user story the task belongs to (US1–US4)
- Paths are from the repository root

---

## Phase 1: Setup

**Purpose**: The decision is recorded and the folders exist.

- [x] T001 Record the owner's choice of Module 6 regression (made 2026-10-26: normalisation, research R1; `>=` to `>` was the alternative), dated, in `docs/decisions.md`; if the alternative is chosen, update R1, FR-008, the patch name and the expected failing test in `contracts/evidence-checklist.md` before going on → row dated 2026-10-26 appended to `docs/decisions.md`
- [x] T002 Create `workshop/advanced/` with empty `solutions/`, `starter/`, `patches/` and `tests/` folders and `workshop/advanced/README.md` (what each folder is; patches are never imported or run in CI; how to point the tests at the starter) → four folders and `workshop/advanced/README.md`
- [ ] T003 Record the number of tests CI collects today (`python -m pytest --collect-only -q`, last line) in the pull request description, to compare in T036 (SC-008)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: The safety guards and the starter/solution loader every story uses.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

- [x] T004 Write failing tests in `workshop/advanced/tests/test_track_safety.py`: no `.py` file under `workshop/advanced/patches/`; every `*.patch` there changes only `src/rice_pest_detector/infer.py`; each applies with `git apply --check` to a copy of that file in `tmp_path`, without importing or running the result; files under `workshop/advanced/solutions/` and `starter/` (except `test_*.py`) import only the standard library; the loader returns `solutions/` by default and `starter/` when `RPD_WORKSHOP_IMPL=starter` → red first (2 failed, 3 errors: no patch, no scripts, no loader); green after T005, T006, T011
- [x] T005 Implement `workshop/advanced/tests/conftest.py`: fixtures `verify_mod` and `workflow_mod` that load the module by file path (`importlib.util.spec_from_file_location`) from `solutions/` or, with `RPD_WORKSHOP_IMPL=starter`, from `starter/` (research R9); the loader part of T004 passes → loader tests pass; `RPD_WORKSHOP_IMPL` other than solutions/starter is refused
- [x] T006 Make `workshop/advanced/patches/m6-normalisation.patch` with `git diff` in a disposable worktree (research R8), adding mean/std normalisation to `preprocess` only; confirm on the light path that exactly `test_preprocess_shape_range_and_no_normalisation` fails with it applied; T004 passes → one added line in `preprocess`; light run with it applied: exit 1, only `test_preprocess_shape_range_and_no_normalisation` failed, 3 passed; applies to CRLF and LF copies
- [x] T007 [P] Create `docs/workshop-advanced/evidence-checklist.md` from `contracts/evidence-checklist.md`, with an opening paragraph on keeping evidence outside the clone and free of secrets → page written; Modules 7 and 8 items copied unchanged from the contract

**Checkpoint**: Guards in place; CI would fail if a bug scenario became importable.

---

## Phase 3: User Story 1 - Module 6, Engineer (Priority: P1) 🎯 MVP

**Goal**: A learner sees the regression caught by the right test and missed by the Stop hook, and builds a fail-closed verifier.

**Independent Test**: The Module 6 walk in `quickstart.md` gives PASS (0), FAIL (1), UNVERIFIED (2), PASS (0), with the evidence files.

### Tests for User Story 1 ⚠️ write first, see them fail

- [x] T008 [P] [US1] Tests for `read_report`: pytest's JUnit XML with passes, failures, errors and skips (counts summed over several `<testsuite>` elements, `failed_tests` names), a missing file and malformed XML (None), in `workshop/advanced/tests/test_verify_report.py` → 8 tests; red (file missing) before T011
- [x] T009 [P] [US1] Tests for `classify` covering rows 2–9 of the decision table in `contracts/verifier-cli.md`, including exit 0 with failures (FAIL), non-zero exit with a clean report (UNVERIFIED), 0 tests, all skipped and fewer than `min_tests`, in `workshop/advanced/tests/test_verify_classify.py` → 16 tests; skipped tests do not count towards `--min-tests` (see the note in the verifier contract row 8)
- [x] T010 [P] [US1] End-to-end tests running `verify.py` with `sys.executable` against tiny projects written into `tmp_path` (one passing test; one failing; none; all skipped; a command that does not exist; a command that sleeps past `--timeout 2`; no `{junit}`; a stale `junit.xml` left in the evidence folder by a command that writes none; a path with a space): exit codes, the `RESULT:` line, and `verification.json`, `run.log` written each time, in `workshop/advanced/tests/test_verify_cli.py` → 17 tests incl. parametrised limits; red before T011

### Implementation for User Story 1

- [x] T011 [US1] Implement `workshop/advanced/solutions/verify.py` per `contracts/verifier-cli.md` and `data-model.md` (standard library only; no shell; top-level catch reports UNVERIFIED) (T008–T010 pass) → 51 track tests pass on the light path; ruff clean
- [x] T012 [US1] Write `workshop/advanced/starter/verify.py`: same command line and function signatures, docstrings from the contract, bodies raising `NotImplementedError` with TODOs; confirm that with `RPD_WORKSHOP_IMPL=starter` T008–T010 fail with `NotImplementedError` and without it they pass → with `RPD_WORKSHOP_IMPL=starter`: 41 failed with `NotImplementedError`, 10 safety tests passed, exit 1; without it all pass
- [ ] T013 [US1] Time the light command (research R3) from an empty `uv` cache on Windows, macOS and Linux; record package count (≤ 10, no torch), time and `uv` version for the page's "Tested with" note (SC-003)
- [x] T014 [US1] Write `docs/workshop-advanced/module-6-engineer.md`: prerequisites, objectives, concepts (the inference contract as the definition of correct; regression; fail-open versus fail-closed; instructions, local hooks and independent CI as three kinds of control, and that the Stop hook belongs to one agent's harness), timed steps (baseline; worktree and patch; see the failure; read and run the Stop hook; build the verifier test-first against the starter with your agent; PASS, FAIL and UNVERIFIED runs; restore and remove the worktree), expected results, troubleshooting (no network for `uv`, paths with spaces, patch applied in the wrong folder), reflection with answers in `<details>`, the Exercise 1 callback paragraph, the teaching-demo statement and primary references; PowerShell and bash where commands differ → page written; research claims marked `[CITE: ...]` for separate sourcing, empty References heading
- [x] T015 [US1] Walk Module 6 end to end in a disposable worktree on one OS following only the page; paste the real `RESULT:` lines and the Stop hook's output into the page's expected results; fix anything the page missed → walked on Windows 11 (bash and PowerShell) at a path with a space: PASS 0, FAIL 1, UNVERIFIED 2, PASS 0; Stop hook exit 0 (Flutter missing); real `RESULT:` lines pasted into the page

**Checkpoint**: Module 6 works on its own: the MVP of the track.

---

## Phase 4: User Story 2 - Module 7, Orchestrate (Priority: P2)

**Goal**: The regression runs through a bounded state machine driven by the verifier's exit code, with a human approval gate.

**Independent Test**: Reproduce both reference traces with the Module 7 walk in `quickstart.md`.

### Tests for User Story 2 ⚠️ write first, see them fail

- [ ] T016 [P] [US2] Tests for every one of the 56 state-event pairs: the 8 allowed pairs reach the `To` state in `contracts/workflow-cli.md`, the 48 others raise `InvalidTransition` and leave the record unchanged, in `workshop/advanced/tests/test_workflow_transitions.py`
- [ ] T017 [P] [US2] Tests for the retry bound: fail, fail, fail → `blocked`/`retry_exhausted`, attempts 3; fail, pass → `awaiting_approval`, attempts 2; unverified on the first attempt → `blocked`/`verification_unavailable`; `--max-attempts 1` blocks on the first fail; 0 and 4 are usage errors, in `workshop/advanced/tests/test_workflow_retries.py`
- [ ] T018 [P] [US2] Tests for the approval gate: `approve` and `reject` only from `awaiting_approval` and only with actor `human`; `verifier_*` events refused by `event`; `reject` sets `rejected_by_human`, in `workshop/advanced/tests/test_workflow_approval.py`
- [ ] T019 [P] [US2] Tests for the record: round-trip; every invariant in `data-model.md`; history append-only (earlier entries byte-identical after a new event); a failed write (patched `os.replace`) leaves the old file; corrupt JSON, a missing file and an invariant violation give exit 4; task IDs such as `../x` and `A` are refused; and that `workshop/advanced/solutions/traces/success.json` and `exhaustion.json` load and end `approved` and `blocked`/`retry_exhausted`, in `workshop/advanced/tests/test_workflow_record.py`
- [ ] T020 [P] [US2] Command-line tests via `sys.executable` with fake verify commands (`python -c "import sys; sys.exit(N)"` for N = 0, 1, 2, 7) and one that cannot start: `start`, `event`, `verify`, `show`; exit codes 0, 2, 3, 4; `verify` refused outside `verifying` without running the command, in `workshop/advanced/tests/test_workflow_cli.py`

### Implementation for User Story 2

- [ ] T021 [US2] Implement `workshop/advanced/solutions/workflow.py` per `contracts/workflow-cli.md` and `data-model.md`, with the transition table as data and atomic writes (T016–T020 pass except the trace check in T019)
- [ ] T022 [US2] Write `workshop/advanced/starter/workflow.py`: the transition table with four rows left as TODO, functions raising `NotImplementedError`; confirm the starter fails T016–T020 for that reason
- [ ] T023 [US2] Produce `workshop/advanced/solutions/traces/success.json` (one fail, repair, pass, approve) and `exhaustion.json` (three fails) by running the real verifier on the patched worktree; replace times and evidence paths with fixed example values; T019 passes in full
- [ ] T024 [US2] Write `docs/workshop-advanced/module-7-orchestrate.md`: concepts (state machine, bounded loop, evidence-driven transitions, human gate, what a local record cannot protect), the manual handoff path with the exact prompts, timed steps for the success and exhaustion runs, an invalid-transition try, expected results, troubleshooting, reflection with answers, and an optional "Connected path" section (an agent's command-line tool driven by a script, tools named alphabetically with the no-endorsement note; a short LangGraph example) labelled optional, connected and not tested in CI
- [ ] T025 [US2] Run the optional LangGraph listing once in a clean environment (`uv run --no-project --with langgraph==<version>`), pin the version and date on the page, or remove the listing if it does not run
- [ ] T026 [US2] Walk Module 7 end to end following only the page; paste the real `show` output into the expected results; fix anything the page missed

**Checkpoint**: Modules 6 and 7 work together without GitHub.

---

## Phase 5: User Story 3 - Module 8, Automate (Priority: P3)

**Goal**: Issue to verified pull request in the learner's own fork, observed by the existing CI, reviewed by a person.

**Independent Test**: In a fresh fork, the pull request and its CI run appear in the fork and nothing appears upstream.

- [ ] T027 [P] [US3] Write `workshop/advanced/solutions/test_m8_reference.py`, the answer to the practice issue: kept detections sorted by descending score; a score equal to a published threshold (0.48) is kept; boxes scale by the orientation-corrected size of a generated JPEG with a rotation tag. They must pass against the unchanged `infer.py`; in a disposable worktree, check by hand that each fails against a matching mutation (sort removed; `>` for `>=`; raw size used) and note the results in the pull request
- [ ] T028 [US3] Write the practice issue text (scope: tests only; must not change thresholds, `infer.py`, the contract or fixtures; done when the verifier passes and CI is green) as an appendix of `docs/workshop-advanced/module-8-automate.md`
- [ ] T029 [US3] Write the rest of `docs/workshop-advanced/module-8-automate.md`: fork; enable Actions and Issues; `gh repo set-default`; file the issue in the fork; branch; agent plans, a person approves; implement; verify locally; `gh pr create --repo <you>/rice-pest-detector --base main` with the warning that the default is upstream; watch checks; review against the checklist; optional ruleset requiring the Python tests check; untrusted inputs (with one example of a smuggled instruction); no secrets, no automatic merge, no deployment; clean-up; reflection with answers; a read-only route for learners without a GitHub account
- [ ] T030 [US3] Re-check every GitHub fact in research R6 in a throwaway fork (Actions and Issues off by default, the CLI's default target, no secrets, `tests.yml` triggered by a pull request to the fork's `main`); record the date and `gh` version on the page and correct R6 if anything differs
- [ ] T031 [US3] Walk Module 8 end to end in a fresh fork following only the page; confirm `gh pr list --repo kurtvalcorza/rice-pest-detector --author @me` shows nothing new; paste the real outputs into the expected results

**Checkpoint**: All three modules work.

---

## Phase 6: User Story 4 - Find and start the track (Priority: P4)

**Goal**: The track is reachable from the course, with set-up in `docs/setup.md` and no change to the core path.

- [x] T032 [P] [US4] Write `docs/workshop-advanced/README.md`: who it is for, prerequisites (core Modules 0–4 and Exercise 1), the time table (45–60, 60–75, 60–90 minutes), what you need (links into `docs/setup.md` only), the agent naming note, the teaching-demo statement, a glossary (verifier, fail-closed, fail-open, regression, worktree, fork, state machine, evidence bundle) and getting help — done 2026-10-28: landing page with the module table (Modules 7–8 marked not written yet), linked from the core course's advanced-track paragraph and file table and from Module 6
- [ ] T033 [US4] Add to `docs/workshop-setup.md` one "Advanced track (optional)" paragraph after Module 5 and one row in "The files you will use"; change nothing else
- [ ] T034 [US4] Add one row to the "I want to…" table in `docs/setup.md` for the advanced track (Git, `uv`, a coding agent; for Module 8 a GitHub account and the GitHub CLI, both already covered there); add an install section only if T013 or T025 found one missing
- [ ] T035 [P] [US4] Mention `workshop/advanced/` and `docs/workshop-advanced/` in `README.md` ("Repository layout" and the workshop bullet under "Who it is for")

---

## Phase 7: Polish and acceptance

- [ ] T036 Run `python -m pytest -q` from the root with the full install, as CI does; all green; the collected count has risen by the number of new tests since T003 (SC-008)
- [ ] T037 Run the light-path command in `quickstart.md` on a fresh `uv` cache; all green with ≤ 10 packages
- [ ] T038 Clean-environment learner acceptance test: at least three testers who did not write the track, at least one each on Windows, macOS and Linux, each on a fresh user account with only Git, `uv`, the GitHub CLI and a coding agent; they follow the pages alone; record per module the time, every blocker and every deviation from an expected result in `docs/workshop-advanced/acceptance-record.md` (SC-001, SC-002, SC-004, SC-005, SC-006)
- [ ] T039 Fix every blocker from T038, adjust any time estimate outside its range, and have the affected steps re-run by a tester
- [ ] T040 Add a throwaway `.py` file to `workshop/advanced/patches/`, confirm the suite fails, remove it (SC-008)
- [ ] T041 Check `git diff --stat main -- src app docs/inference-contract.md .claude .github pyproject.toml requirements.txt` is empty and the diff to `docs/workshop-setup.md` is only the paragraph and the row (SC-007, SC-009)
- [ ] T042 Check every new page: the teaching-demo statement is present; tools are named only alphabetically with the no-endorsement note; LangGraph only in the optional section; no institution names, no personal paths, no keys (SC-010, FR-005, FR-006)

---

## Dependencies & Execution Order

### Phase dependencies

- **Setup (Phase 1)** → **Foundational (Phase 2)** → user stories. T001 blocks T006.
- **US1 (Phase 3)** first: US2 uses its verifier; US3 uses both.
- **US4 (Phase 6)** can be written alongside US2 and US3, but T033 lands only when all three module pages exist.
- **Polish (Phase 7)** last; T038 needs every page finished.

### Within each story

- Tests first, failing for the right reason (Principle III); then the reference; then the starter; then the page; then an end-to-end walk.
- Each story ends with the whole suite green and a commit.

### Parallel opportunities

- T007 with T004–T006.
- US1: T008, T009, T010 together.
- US2: T016–T020 together.
- US3: T027 with T028.
- US4: T032 and T035 together.

## Implementation Strategy

### MVP first (User Story 1 only)

1. Phases 1 and 2, after the owner's confirmation (T001).
2. Phase 3: **stop and validate** with one tester before Module 7, because the verifier's exit codes are Module 7's input.

### Incremental delivery

US1 (Module 6) → US2 (Module 7) → US3 (Module 8) → US4 (links), each a commit with green tests; the core course page changes only in the last step.
