# Research: Advanced Workshop Track

**Feature**: [spec.md](spec.md) | **Plan**: [plan.md](plan.md) | **Date**: 2026-10-26

Facts marked **checked** were read in this repository (file:line) or run on 2026-10-26 in a scratch copy of `pyproject.toml`, `src/` and `tests/test_infer.py` with `uv` 0.13.5 on Windows. Facts marked **to re-check** are about hosted tools and are re-checked when the pages are written (task T030).

## R1. Which regression Module 6 uses

**Decision (owner, 2026-10-26)**: Add mean/std normalisation to `preprocess` (the common ImageNet values, `(x - [0.485, 0.456, 0.406]) / [0.229, 0.224, 0.225]`). Mention Exercise 1 in one paragraph: there, a test pinned a boundary in arithmetic; here, a test pins a line of a written contract that an agent following common practice would "fix".

**Rationale**:

- **Already caught.** `test_preprocess_shape_range_and_no_normalisation` (`tests/test_infer.py:8-12`) asserts a pure red image gives exactly 1.0 and 0.0 in its first two channels. Checked: with the patch, that test fails and the other three pass.
- **A new lesson, not a repeat.** Exercise 1 already teaches the `>` versus `>=` boundary (`docs/workshop-setup.md:167`, `:235`). Normalisation is the mistake an agent is likely to make on its own: most vision tutorials normalise, and the contract says "**None.**" (`docs/inference-contract.md:16`). It teaches that the contract, not the agent's habits, defines correct.
- **The control lesson is sharper.** Only one Python test guards this line. The app's fixture tests do not touch `preprocess` (no `preprocess` call in `tools/export_app_fixtures.py`), and the Stop hook runs `flutter test` against committed fixtures (`.claude/hooks/require_green_tests.py:52`), so nothing local except that one test stops it.

**Alternatives considered**:

| Option | For | Against |
| :-- | :-- | :-- |
| `scores >= threshold` → `scores > threshold` (the issue's proposal), framed as "the same bug class, now in real code" | Caught by `tests/test_infer.py:20-30` (checked: exactly one failure) and again by `tests/test_export_app_fixtures.py:64-77` in the full suite; a direct callback to Exercise 1 | Repeats Exercise 1's lesson (review point 1); a learner who did Exercise 1 learns less |
| Scale boxes by the raw size instead of the orientation-corrected size | A real, silent failure on rotated phone photos (`docs/inference-contract.md:63`) | Not caught by `tests/test_infer.py`: `postprocess` receives `width` and `height` from its caller (`src/rice_pest_detector/infer.py:29-36`); the test passes fixed sizes (`tests/test_infer.py:26`). The size is chosen in callers such as `tools/kaggle_driver.py:356`. Kept as part of Module 8's practice issue, where writing that test is the work |
| Ship two patches and let the learner pick | Covers both lessons | Doubles the module's steps and its acceptance testing for a 45–60 minute slot |

## R2. The verifier: fail-closed design

**Decision**: A standard-library Python script, `verify.py`, that runs a given command and judges it by two independent signals: the command's exit code and a JUnit XML report the command writes to a path the verifier chooses (the `{junit}` placeholder). PASS needs both: exit 0, and a fresh report with at least `--min-tests` tests, 0 failures, 0 errors and at least one test that was not skipped. The full decision table is in [contracts/verifier-cli.md](contracts/verifier-cli.md).

**Rationale**:

- **Fail-closed means the default answer is "not verified".** Every case the verifier cannot positively confirm (command not found, timeout, crash, no report, unreadable report, zero tests, all skipped, too few tests, a report that passes while the command failed) is UNVERIFIED, exit 2. This is the opposite of the Stop hook, which allows the stop when it cannot run (`.claude/hooks/require_green_tests.py:21-22`, `:48-49`, `:55-56`) or after one block (`:26-28`); the module puts the two side by side.
- **Independent observation.** The exit code alone can be faked or misread (a wrapper script that swallows failures exits 0). The report shows how many tests ran. `--min-tests 4` for `tests/test_infer.py` catches a silently deselected or deleted test.
- **No stale evidence.** The verifier deletes the report path before running, so an old passing report cannot count.
- **Agent- and runner-neutral.** It takes any command after `--`. JUnit XML is written by pytest's built-in `--junitxml` and by many other runners, so the same verifier fits other projects.
- **Exit codes 0/1/2.** Three codes keep the workflow's rule simple: 1 is worth repairing (the tests ran and said no); 2 is not (nothing trustworthy happened). A report that shows failures is FAIL even if the command exited 0, because a failure in a report is evidence; the reverse (report passes, command failed) is UNVERIFIED.

**Alternatives considered**: Exit code only (rejected: cannot tell "0 tests ran" from "all passed"; pytest exits 5 for no tests, but other runners exit 0); parse pytest's console text (rejected: changes between versions and is runner-specific); a pytest plugin (rejected: ties the verifier to pytest and to the environment under test).

## R3. The light command for the core path

**Decision**: From the repository root (or the disposable worktree):

```bash
uv run --no-project --python 3.12 --with numpy==2.5.4 --with pillow==13.0.0 --with pytest --with-editable . python -m pytest tests/test_infer.py
```

**Rationale**: Checked on 2026-10-26: it built the package, installed 9 packages (no PyTorch) and passed 4 tests in about 10 seconds with a warm cache. It follows Exercise 1's style (`uv run --no-project ...`, `docs/workshop-setup.md:187`). Python 3.12 matches `requires-python = ">=3.12,<3.13"` (`pyproject.toml:8`); NumPy and Pillow are pinned as in `pyproject.toml:10`. `--with-editable .` makes the package importable and makes edits (the patch) visible at once; pytest's configured `pythonpath = ["."]` (`pyproject.toml:24`) does not reach `src/`. The editable build writes `src/rice_pest_detector.egg-info/`, which `.gitignore` already ignores (`*.egg-info/`).

**Alternatives considered**: `uv run --with pytest` without `--no-project` (rejected: it syncs the project and writes a `uv.lock` into the clone, an untracked file learners would have to clean up); the full install in `docs/setup.md` "Python tools and tests" (rejected: installs PyTorch; review point 3); setting `PYTHONPATH=src` (rejected: different syntax in PowerShell and bash).

## R4. The workflow state machine and its history

**Decision**: A standard-library script, `workflow.py`, with a transition table held as data (7 states, 8 events; [contracts/workflow-cli.md](contracts/workflow-cli.md)). One JSON file per task in a learner-chosen state folder, holding the current state and an append-only `history` list. Writes go to a temporary file in the same folder, then `os.replace`, so a crash leaves the old record whole. The `verify` command runs the task's stored verify command and maps its exit code to `verifier_pass`, `verifier_fail` or `verifier_unverified`; those three events cannot be sent by hand.

**Rationale**:

- **Transitions from evidence, not claims.** The agent can say "done", which moves the task to verifying; only the verifier's exit code moves it on.
- **A bounded loop.** At most 3 verification attempts per task (the issue's bound; values 1–3 allowed for practice). Bounding is what makes the loop safe to leave running; the Stop hook's one-block rule (`.claude/hooks/require_green_tests.py:26-28`) is the same idea with a bound of 1.
- **A table as data** is easy to test exhaustively (56 pairs, SC-005) and easy for a learner to read.
- **JSON with a history list** is readable in any editor and diffable in Git; one file per task avoids locking between tasks.

**Alternatives considered**: JSON Lines append-only log (rejected: current state must be recomputed, and a half-written last line needs repair logic); SQLite (rejected: not readable without a tool; more than the lesson needs); LangGraph as the core engine (rejected for the core path: a dependency and a framework to learn before the idea; kept as an optional example, R5); keeping state in memory only (rejected: the history is the evidence).

**Limit stated to learners**: the record is a local file and the "human" actor is not authenticated. The approval gate is a process control. Real systems put approval where the agent cannot write, which is why Module 8 moves it to a pull-request review.

## R5. Manual versus connected agent path

**Decision**: The core path is manual. The learner copies a prompt (given in the page) into their agent, reads the result, and runs `workflow.py event <task> implementation_done` (or `repair_done`) themselves; `workflow.py verify` does the checking. An optional section shows a connected path: a short driver that calls an agent's command-line tool non-interactively, or a LangGraph graph with the same states, each labelled "optional, connected, not tested in CI".

**Rationale**: Manual handoffs work with any agent the learner is allowed to use, need no API key, and keep a person reading every step, which is the course's stance (Module 4's safe defaults). A connected path is where real systems go, so it is shown, but it needs credentials, non-interactive permission settings and cost controls that the core path should not require.

**Alternatives considered**: Connected by default (rejected: excludes learners whose agent has no CLI or who may not use API keys, and invites unattended execution); no connected path at all (rejected: the issue asks for it as an extension, and without it "orchestration" stays abstract).

## R6. Fork and pull-request flow for Module 8

**Decision**: The learner forks the repository with the GitHub CLI, enables Actions and Issues on the fork, sets the fork as the CLI's default repository, files the practice issue there, works on a branch, and opens the pull request with an explicit target:

```bash
gh repo fork kurtvalcorza/rice-pest-detector --clone
gh repo set-default <you>/rice-pest-detector
gh repo edit <you>/rice-pest-detector --enable-issues
gh issue create --repo <you>/rice-pest-detector
gh pr create --repo <you>/rice-pest-detector --base main --head <branch>
gh pr checks --repo <you>/rice-pest-detector --watch
```

Facts to re-check (T030): Actions are disabled on a new fork until the owner enables them in the Actions tab; Issues are off on forks by default; in a fork's clone the GitHub CLI proposes the parent repository as the pull request's base unless told otherwise, and the web page's "Compare & pull request" also targets the parent; workflows in a fork get none of the parent's secrets, and this repository's workflow uses none (`.github/workflows/tests.yml:10-11` grants `contents: read` only). `tests.yml` runs on pull requests to `main` (`.github/workflows/tests.yml:6-7`), so a pull request to the fork's `main` triggers it once Actions are on.

**Alternatives considered**: A new, empty practice repository (rejected: loses the real CI and history the module is about); pull requests to upstream on a practice branch (rejected: the issue and review forbid it, and it would put learner work in the public repository's notifications); a template repository (rejected: this repository is not a template, and making one changes upstream settings).

## R7. Where the track's tests run in CI

**Decision**: In the existing Python job's `python -m pytest -q` step (`.github/workflows/tests.yml:39-40`), with no workflow change. pytest from the repository root collects every `test_*.py` because `pyproject.toml` sets no `testpaths` (`pyproject.toml:22-25`), so `workshop/advanced/tests/` is picked up automatically. The tests target the reference solutions. A safety test checks that the patch folder contains no `.py` files and that each patch applies (`git apply --check`) to a temporary copy of the file it changes; it never imports or runs the patched code.

**Rationale**: Reuses the existing control (review point 5, constitution Principle VII). The same root-wide collection is why bug scenarios must not be Python files: any `test_*.py` under `workshop/` would be collected and run.

**Alternatives considered**: A separate workflow or job (rejected: redundant CI, issue says avoid it); excluding the track from CI (rejected: untested course code rots and violates Principle III); running the patched code in CI to prove it fails (rejected: review point 5 says CI never runs bug scenarios; the apply check is enough to keep the patch current, and acceptance testing shows the failure).

## R8. How disposable worktrees are created

**Decision**: A sibling worktree on a new branch, the same pattern the course already uses (`docs/workshop-setup.md:350`, `:362`):

```bash
git worktree add ../rpd-m6 -b m6-practice
cd ../rpd-m6
git apply workshop/advanced/patches/m6-normalisation.patch
# ... the module's steps ...
cd ../rice-pest-detector
git worktree remove --force ../rpd-m6
git branch -D m6-practice
```

Evidence goes to `agents-practice/advanced-evidence/m6/` (the practice folder from Module 0), outside both the clone and the worktree, so removing the worktree keeps it.

**Rationale**: The bug never touches the learner's main checkout; one command removes it; `git worktree list` shows where it is. `git apply` needs no commit and no network.

**Alternatives considered**: A second full clone (rejected: slower, more disk, easy to confuse with the real one); a branch in the main checkout (rejected: the bug sits in the learner's working copy and is easy to commit by mistake); a copy made by a script (rejected: one more tool to trust).

## R9. Starter files and reference solutions

**Decision**: `workshop/advanced/solutions/` holds the reference `verify.py` and `workflow.py`; `workshop/advanced/starter/` holds the same files with the same signatures and `NotImplementedError` bodies marked TODO. The tests in `workshop/advanced/tests/` load the module by file path through a fixture in `conftest.py`: from `solutions/` by default, from `starter/` when the environment variable `RPD_WORKSHOP_IMPL` is `starter`. CI never sets it.

**Rationale**: One set of tests is the specification for both; the learner works test-first against the starter (red, then green), CI keeps the reference green. Loading by path avoids putting a generic module name such as `verify` on `sys.path`.

**Alternatives considered**: Tests copied into the learner's practice folder (rejected: two copies drift); a pytest command-line option (rejected: options declared in a sub-folder `conftest.py` are not seen when pytest runs from the root, as CI does).
