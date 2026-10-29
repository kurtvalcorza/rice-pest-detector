# Implementation Plan: Advanced Workshop Track

**Branch**: `004-advanced-workshop` | **Date**: 2026-10-26 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/004-advanced-workshop/spec.md`

## Summary

Add an optional advanced track of three modules to the *Coding with AI Agents* course, built on the repository's real inference code. New code is two small standard-library scripts (a fail-closed verifier and a bounded workflow state machine) with their tests, starter versions for learners, one regression patch, and four course pages. Nothing in the detector, the app, the inference contract, the Stop hook or CI changes; the track's tests run inside CI's existing `python -m pytest` step. The main design choices are in [research.md](research.md): the regression (R1, owner to confirm), the verifier (R2), the light `uv` command (R3), the workflow (R4), the fork flow (R6) and where intentional bugs live (R7, R8).

## Technical Context

**Language/Version**: Python 3.12 (the repository's `requires-python`), standard library only for the new scripts; Markdown for the course pages

**Primary Dependencies**: None new. pytest (already a dev dependency) runs the tests; `uv` (already in `docs/setup.md`) runs the light path; the GitHub CLI (already in `docs/setup.md`) for Module 8. LangGraph appears only in an optional, untested-in-CI listing

**Storage**: Files only. Verifier evidence (result JSON, run log, JUnit XML) and workflow records (one JSON file per task) in a folder the learner names, by default under `agents-practice/advanced-evidence/<module>/`

**Testing**: pytest, collected from the repository root by CI's existing step; tests load either the reference solutions (default) or the starter (`RPD_WORKSHOP_IMPL=starter`); clean-environment learner acceptance tests on Windows, macOS and Linux (SC-001)

**Target Platform**: A learner's computer (Windows 10/11 with PowerShell, macOS, Linux) with Git, `uv`, a coding agent and, for Module 8, the GitHub CLI and a GitHub account; CI on `ubuntu-24.04`

**Project Type**: Course content plus two command-line teaching tools, inside the existing repository

**Performance Goals**: Baseline command under 2 minutes on first run, seconds after (SC-003); the track's tests add under 30 seconds to CI's Python job

**Constraints**: No change to published inference behaviour (FR-029); intentional bugs only as patches (FR-030); no new CI workflow (FR-026); light path ≤ 10 packages, no PyTorch (SC-003); agent tools named only as alphabetical examples with the no-endorsement note (FR-005)

**Scale/Scope**: 3 modules (about 2.75–3.75 hours), 4 new pages, 2 scripts (about 150 and 250 lines), 2 starter scripts, 1 patch, about 60 new tests, 1 paragraph and 1 table row added to the core course page, 1 table row in `docs/setup.md`

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Check | Before research | After design |
| :-- | :-- | :-- | :-- |
| I. Teaching demo, not a field tool | No app strings change. Every page states that passing tests are not accuracy or field suitability (FR-006); Module 8's issue forbids threshold changes | Pass | Pass: wording check is task T042 |
| II. One inference contract | `infer.py`, the contract, fixtures and every client are untouched (FR-029). The regression exists only as a patch applied in a disposable worktree (R8) | Pass | Pass: SC-007 diff check (T041); the patch-apply test never imports the patched file (R7) |
| III. Test-first, green before done | Tests for the verifier and workflow are written before them and run in CI's existing step; the whole suite stays green. No generated files are added, so no new `--check` mode is needed; the patch is guarded by an apply check instead | Pass | Pass: each story's tests precede its code in tasks.md |
| IV. Rules fixed before results | No thresholds, calibration or model choice involved; Module 8's practice issue fixes "tests only" before the agent starts | Pass (not affected) | Pass |
| V. Local and Private by Default | Applies to the apps' photos and history; this feature adds no app code. The scripts make no network calls; evidence stays in the learner's folder; Module 8's network use is the learner's own explicit `gh` commands to their own fork | Pass (not affected) | Pass |
| VI. Verified models only | No model is loaded on the core path | Pass (not affected) | Pass |
| VII. Shared sources, simplest thing | Reuses `tests/test_infer.py`, the Stop hook, `tests.yml`, `docs/setup.md` and the course page; standard library only; no new workflow. One extra layer: the starter/solution loader (Complexity Tracking) | Pass with one justified item | Pass: still one item |
| Development workflow | Spec before code (this folder); PRs pass CI before merging; decisions recorded | Pass | Pass: the regression choice goes to `docs/decisions.md` once confirmed (T001) |

## Project Structure

### Documentation (this feature)

```text
specs/004-advanced-workshop/
├── plan.md              # This file
├── research.md          # Phase 0: R1–R9 decisions
├── data-model.md        # Phase 1: verifier result, workflow record, transition, evidence bundle
├── quickstart.md        # Phase 1: run the track's tests and walk the three modules as a maintainer
├── contracts/
│   ├── verifier-cli.md        # verify.py: arguments, decision table, exit codes, output files
│   ├── workflow-cli.md        # workflow.py: states, events, transitions, record format, exit codes
│   └── evidence-checklist.md  # What a learner keeps and checks, per module
├── checklists/
│   └── requirements.md  # Spec quality checklist
└── tasks.md             # Phase 2
```

### Source code and pages (repository root)

The issue's provisional layout is revised for review point 5: no `scenarios/` folder of buggy code; the regression is a `.patch` file, and nothing under `workshop/` is a modified copy of source code.

```text
docs/
├── workshop-setup.md                 # + one "Advanced track (optional)" paragraph after Module 5, + one file-table row
├── setup.md                          # + one row in "I want to…" (installs already documented there)
└── workshop-advanced/
    ├── README.md                     # landing: who, prerequisites, time, what you need, agent note, glossary
    ├── module-6-engineer.md
    ├── module-7-orchestrate.md
    ├── module-8-automate.md
    ├── evidence-checklist.md         # the learner's copy of contracts/evidence-checklist.md
    └── acceptance-record.md          # clean-environment acceptance results (SC-001, SC-002)

workshop/advanced/
├── README.md                         # what each folder is; "patches are never imported or run in CI"
├── solutions/
│   ├── verify.py                     # reference verifier (contracts/verifier-cli.md)
│   ├── workflow.py                   # reference workflow (contracts/workflow-cli.md)
│   ├── test_m8_reference.py          # reference answer to Module 8's issue; passes on unchanged infer.py
│   └── traces/
│       ├── success.json              # Module 7 reference: fail, repair, pass, approve
│       └── exhaustion.json           # Module 7 reference: three fails, blocked
├── starter/
│   ├── verify.py                     # same signatures, TODO bodies
│   └── workflow.py
├── patches/
│   └── m6-normalisation.patch        # the only intentional bug; applied in a disposable worktree
└── tests/
    ├── conftest.py                   # loads solutions/ (default) or starter/ (RPD_WORKSHOP_IMPL=starter) by file path
    ├── test_track_safety.py          # no .py in patches/; each patch touches only infer.py and applies to a temp copy
    ├── test_verify_report.py
    ├── test_verify_classify.py
    ├── test_verify_cli.py
    ├── test_workflow_transitions.py
    ├── test_workflow_retries.py
    ├── test_workflow_approval.py
    ├── test_workflow_record.py
    └── test_workflow_cli.py

README.md                             # repository layout and the workshop bullet mention the track
```

Unchanged on purpose: `src/`, `app/`, `docs/inference-contract.md`, `tests/test_infer.py`, `.claude/`, `.github/workflows/tests.yml`, `pyproject.toml`, `requirements.txt`, the slides.

**Structure Decision**: Pages under `docs/workshop-advanced/` beside the core course page; runnable material under `workshop/advanced/`, split into `solutions/`, `starter/`, `patches/` and `tests/`. `workshop/advanced/solutions/test_m8_reference.py` is collected by CI on purpose: it holds correct tests for the real code, not a bug.

## Complexity Tracking

| Violation | Why needed | Simpler alternative rejected because |
| :-- | :-- | :-- |
| Starter/solution switch (`RPD_WORKSHOP_IMPL` read by `workshop/advanced/tests/conftest.py`) — an extra layer under Principle VII | Learners work test-first against the starter with the same tests CI runs on the reference; one set of tests, two targets | Copying the tests into the practice folder makes two copies that drift; a pytest option in a sub-folder `conftest.py` is not registered when pytest runs from the root (R9) |
