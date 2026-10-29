# Feature Specification: Advanced Workshop Track (Engineer, Orchestrate, Automate)

**Feature Branch**: `004-advanced-workshop`

**Created**: 2026-10-26

**Status**: Draft, awaiting owner review of issue #3

**Input**: GitHub issue #3, "Expand Coding with AI Agents workshop: harness, orchestration, and software factory modules", and its review comment (seven owner-approved changes). Add three cumulative modules that take a learner from using a coding agent to engineering a controlled agent workflow, on this repository's real inference code, as a separate advanced track that leaves the core course as it is.

## User Scenarios & Testing *(mandatory)*

The learner has finished the core course (Modules 0–4 and Exercise 1 in `docs/workshop-setup.md`). The three modules are cumulative: Module 7 reuses Module 6's verifier and regression, and Module 8 reuses both. The whole track takes about 2.75–3.75 hours (45–60 + 60–75 + 60–90 minutes), on top of the core course's three hours.

### User Story 1 - Module 6, Engineer: protect the inference contract (Priority: P1)

A learner breaks the real detector's preprocessing on purpose, in a throwaway copy of the repository, watches the right test catch it, learns that the repository's Stop hook does not, and builds a small verifier that says PASS only when tests really ran and passed.

**Why this priority**: Modules 7 and 8 both drive their decisions from this verifier. It is also the module that carries the track's main lesson: a control protects only what it checks.

**Independent Test**: From a fresh clone, run the baseline command, apply the Module 6 patch in a disposable worktree, and run the reference verifier three times: on the patched code (FAIL), on the restored code (PASS) and with the test runner unavailable (UNVERIFIED). Each run gives its documented exit code and evidence files.

**Acceptance Scenarios**:

1. **Given** a clone and `uv`, **When** the learner runs the documented baseline command, **Then** the four tests in `tests/test_infer.py` pass, and the environment holds NumPy, Pillow, pytest and the package, with no PyTorch, Flutter, emulator or model weights.
2. **Given** a disposable worktree with the Module 6 patch applied, **When** the learner runs the tests, **Then** exactly one test fails (`test_preprocess_shape_range_and_no_normalisation`) and the module explains which line of the inference contract the patch broke.
3. **Given** the same patched worktree, **When** the learner reads or runs the Stop hook, **Then** the module shows that the hook runs `flutter test` on the app, never `pytest` on `infer.py`, so it would let an agent finish with this regression in place; and it lists the hook's three fail-open cases (switched off, Flutter missing, already blocked once).
4. **Given** the verifier, **When** the tests pass, fail, or cannot run (runner missing, timeout, no report, zero tests, every test skipped), **Then** it reports PASS (exit 0), FAIL (exit 1) or UNVERIFIED (exit 2) respectively, and never PASS unless a fresh test report shows at least the expected number of tests run and none failed.
5. **Given** the end of the module, **When** the learner removes the worktree, **Then** their clone's `main` is unchanged and they hold an evidence bundle: the three verifier results, the test output, the diff and their answers to the reflection questions.

---

### User Story 2 - Module 7, Orchestrate: a bounded agent loop (Priority: P2)

A learner runs the same regression through a small state machine (plan, implement, verify, repair, human approval, blocked), where only the verifier's exit code moves the task forward, repairs stop after three verification attempts, and nothing is approved without a person.

**Why this priority**: It turns the verifier from a tool into a gate. It depends on Story 1.

**Independent Test**: With the reference workflow, run one task that fails verification once, is repaired and then passes and is approved, and a second task that fails three times and ends blocked; both records show every transition with its actor and verification result.

**Acceptance Scenarios**:

1. **Given** a new task, **When** the learner records the plan as accepted and the implementation as done, **Then** the task is waiting for verification and no other event can move it except a verifier run.
2. **Given** a task waiting for verification, **When** the verifier exits 0, **Then** the task waits for human approval; **When** it exits 1 and fewer than three attempts have been used, **Then** the task goes to repair; **When** it exits 1 on the third attempt, **Then** the task is blocked with reason "retry exhausted"; **When** it exits 2 (or any other code), **Then** the task is blocked with reason "verification unavailable".
3. **Given** any state, **When** an event arrives that the transition table does not allow (for example "approve" while verifying, or an agent claiming a verifier result), **Then** it is rejected with a clear message and the record is unchanged.
4. **Given** a task waiting for approval, **When** a person approves or rejects it, **Then** it ends approved or blocked, and the record names the person as the actor.
5. **Given** any task, **When** the learner opens its record, **Then** it shows the task ID, current state, attempts used, the last verification result and the full, append-only transition history.
6. **Given** the core path, **When** the learner hands work to the agent, **Then** they do it by hand (copy the prompt, run the event command); a connected path (an agent's command-line tool driven by a script, or a LangGraph graph) is offered only as an optional extension and labelled as such.

---

### User Story 3 - Module 8, Automate: from issue to verified pull request (Priority: P3)

A learner files a small, contract-preserving issue in their own fork, has an agent plan and implement it on a branch, checks it with the verifier, opens a pull request against their fork (never upstream), watches the fork's existing CI run, and reviews it themselves.

**Why this priority**: It shows the whole factory end to end, but needs a GitHub account and depends on Stories 1 and 2.

**Independent Test**: In a fresh fork, follow the module; the pull request appears in the fork, the fork's existing Tests workflow runs on it, and no pull request or issue is created in the upstream repository.

**Acceptance Scenarios**:

1. **Given** a new fork, **When** the learner follows the set-up steps, **Then** they enable Actions (off by default on a new fork) and Issues, and set their fork as the default repository for the GitHub CLI.
2. **Given** the practice issue (more tests for detection ordering, the inclusive threshold at a published model's threshold, and box scaling with the orientation-corrected size), **When** the agent implements it, **Then** the diff changes only test files; no threshold, no `infer.py` line and no contract text changes.
3. **Given** the branch is ready and the verifier passes, **When** the learner opens the pull request with an explicit target (`gh pr create --repo <you>/rice-pest-detector --base main`), **Then** it is opened in the fork; the module warns that without the explicit target the GitHub CLI and web page default to the upstream repository.
4. **Given** the pull request, **When** CI runs, **Then** the learner sees the fork's existing checks (Python tests with the notebook and fixture checks, and Flutter analysis and tests) without adding a workflow, and records the result.
5. **Given** the pull request, **When** the learner reviews it, **Then** they record a review against the evidence checklist and decide by hand whether to merge in their fork; nothing merges automatically and nothing deploys.
6. **Given** the issue and pull-request text, **When** the module discusses them, **Then** it treats both as untrusted input to the agent, and states that forks have no secrets and that the exercise uses no secrets, no unattended privileged commands, no automatic merge and no deployment.

---

### User Story 4 - Find and start the advanced track without disturbing the core course (Priority: P4)

A learner who finished the core course finds the advanced track from the course page, sees what it needs and how long it takes, and starts it; a learner doing only the core course sees nothing different except a link.

**Why this priority**: Navigation and set-up wrap the modules; the modules are useful from their own pages without it.

**Independent Test**: Open `docs/workshop-setup.md`, follow the link to the track, and confirm that its landing page lists prerequisites, time per module, what to install (linking to `docs/setup.md`), the agent naming note and a glossary; confirm the core course text is unchanged apart from the link.

**Acceptance Scenarios**:

1. **Given** the course page, **When** the learner reaches the end of Module 5, **Then** a short paragraph links to the advanced track and says it is optional and takes about 2.75–3.75 hours.
2. **Given** the track's landing page, **When** the learner reads "What you need", **Then** every install is a link into `docs/setup.md`; the course pages contain run commands only.
3. **Given** any page of the track, **When** it names an agent or a tool, **Then** names appear only as examples, in alphabetical order, with the no-endorsement note that `docs/setup.md` uses; LangGraph appears only as one optional example.

---

### Edge Cases

- `uv` has no network on first run: the baseline command cannot fetch Python or packages; the module says it needs network once, then works from the cache.
- The learner applies the patch in their main clone instead of the worktree: the module's check step (`git worktree list` and `git status` in the clone) shows it, and the clean-up step restores the file.
- The patch no longer applies because `infer.py` changed upstream: a workshop test in CI fails first, so the maintainer updates the patch before learners hit it.
- The agent "fixes" the failure by editing or deleting the test: the verifier still says PASS if the remaining tests pass and the count is met; the module uses this to teach reading the diff and pinning the expected test count.
- Fewer tests run than expected (a test deselected, renamed or skipped): the verifier says UNVERIFIED.
- An old test report is left over from an earlier run: the verifier deletes it before running, so a stale PASS cannot be reused.
- The test command succeeds but its report shows failures, or the report shows success but the command failed: the verifier says FAIL in the first case and UNVERIFIED in the second.
- The workflow record is edited by hand or deleted: the workflow refuses a corrupt or missing record; the module says a local file is a process control, not a tamper-proof one.
- A path contains spaces (common on Windows): every command in the pages is quoted and is tested on such a path.
- PowerShell and bash differ (environment variables, line continuation): every command that differs is given for both.
- Actions or Issues are not enabled on the fork: no checks appear, or `gh issue create` fails; the troubleshooting section names both.
- The learner has no GitHub account, or may not create one: Modules 6 and 7 work without it; Module 8 can be read, with the reference evidence as the answer.
- The fork's CI takes longer than the module allows (the Flutter job): the module says to move on and come back to the result.

## Requirements *(mandatory)*

### Functional Requirements

**Track structure**

- **FR-001**: The three modules MUST be published as a separate, optional advanced track with its own landing page; the core course keeps its content, order and three-hour estimate, and gains only a link paragraph and a row in its file table.
- **FR-002**: Every module page MUST state prerequisites, objectives, the concepts it teaches, timed steps, the expected result of each step, troubleshooting, reflection questions with model answers (hidden until opened), and links to primary references.
- **FR-003**: The track MUST state its time: Module 6 45–60 minutes, Module 7 60–75 minutes, Module 8 60–90 minutes, about 2.75–3.75 hours in all.
- **FR-004**: Any install the track needs MUST be documented in `docs/setup.md`; the track's pages MUST link to it and contain run commands only.
- **FR-005**: Agent tools MUST be named only as examples, in alphabetical order, with the no-endorsement note used in `docs/setup.md`; LangGraph MAY appear only as one optional example.
- **FR-006**: Every module MUST say that passing software tests shows the code meets its written contract, not that the model is accurate, validated in the field or suitable for decisions about crops.

**Module 6: Engineer**

- **FR-007**: The core path of Modules 6 and 7 MUST run with one documented `uv` command that installs only NumPy and Pillow at the repository's pinned versions, pytest, and the package itself, in the style of Exercise 1 (`uv run --no-project ...`); no PyTorch, Flutter, emulator or model weights.
- **FR-008**: Module 6 MUST use one intentional regression in `src/rice_pest_detector/infer.py` that `tests/test_infer.py` already catches, chosen in research R1 (owner decision, 2026-10-26: adding mean/std normalisation to `preprocess`), and MUST relate it explicitly to Exercise 1's exactly-100 lesson.
- **FR-009**: The regression MUST ship as a patch file applied in a disposable Git worktree created by a documented command, never as a modified copy of source code in the repository.
- **FR-010**: Module 6 MUST show that the Stop hook runs `flutter test` and cannot see a change to `infer.py`, list its fail-open cases, and distinguish three kinds of control: agent instructions (`AGENTS.md`, skills), local hooks (one agent's harness only) and independent CI.
- **FR-011**: The verifier MUST work with any agent or none, run a given test command, and report PASS only when the command exits 0 and a fresh test report shows at least the required number of tests run with none failed or in error; every other outcome is FAIL or UNVERIFIED (fail-closed).
- **FR-012**: The verifier MUST exit 0 for PASS, 1 for FAIL and 2 for UNVERIFIED, print one result line with its reason, and write its result, the run's output and the test report to an evidence folder.
- **FR-013**: Module 6 MUST have the learner produce a PASS, a FAIL and an UNVERIFIED result, each observable from files without trusting the agent's account.

**Module 7: Orchestrate**

- **FR-014**: The workflow MUST have the states planning, implementing, verifying, repairing, awaiting approval, approved and blocked, and only the transitions in `contracts/workflow-cli.md`.
- **FR-015**: Only a verifier run started by the workflow MAY move a task out of verifying; no command MAY record a verifier result on the agent's or learner's word.
- **FR-016**: Verification attempts MUST be limited to at most three per task; a third failure ends the task blocked with reason "retry exhausted"; an UNVERIFIED result ends it blocked with reason "verification unavailable".
- **FR-017**: Only a person MAY approve or reject a task, and only while it awaits approval.
- **FR-018**: Each task MUST keep a record with its ID, state, attempts, last verification result and an append-only transition history (time, actor, event, from, to); writes MUST be atomic, and a missing or corrupt record MUST stop the workflow with an error.
- **FR-019**: An event that is not allowed in the current state MUST be rejected with a non-zero exit and leave the record unchanged.
- **FR-020**: Module 7's core path MUST use manual handoffs to the agent; any connected path MUST be optional and labelled as connected and not tested in CI.
- **FR-021**: Module 7 MUST show a success run (with at least one repair) and a retry-exhaustion run, with their records as reference traces.

**Module 8: Automate**

- **FR-022**: Module 8 MUST run in a learner-owned fork (or another learner-owned practice repository) and MUST NOT direct any issue or pull request to the upstream repository.
- **FR-023**: Module 8 MUST include an explicit step that targets the learner's fork when opening the pull request, and MUST say that the GitHub CLI and web page otherwise default to the upstream repository.
- **FR-024**: Module 8 MUST tell the learner to enable Actions and Issues on the new fork, and MUST say that forks have no secrets and the exercise needs none.
- **FR-025**: The practice issue MUST be contract-preserving: tests only, with no change to thresholds, `infer.py`, the inference contract or the app's fixtures.
- **FR-026**: Module 8 MUST use the repository's existing `.github/workflows/tests.yml` as the independent check and MUST NOT add a workflow.
- **FR-027**: Module 8 MUST cover human review and, where the learner's plan allows it, a branch ruleset that requires the Python tests check; it MUST NOT use automatic merge, unattended privileged execution or deployment.
- **FR-028**: Module 8 MUST explain why issue and pull-request text are untrusted input to an agent, with at least one concrete example of an instruction an issue might smuggle in.

**Safety of the repository**

- **FR-029**: Nothing in this feature MAY change the published inference behaviour: `src/rice_pest_detector/`, `docs/inference-contract.md`, the app and its fixtures stay as they are.
- **FR-030**: Intentional bugs MUST exist only as patch files; no Python file MAY sit in the patch folder, and nothing in the repository MAY import a patched module.
- **FR-031**: CI MUST run the track's own tests, through the existing `python -m pytest` step, and MUST NOT run the bug scenarios; it MAY check that each patch still applies to a temporary copy, without importing or running the result.
- **FR-032**: The verifier and workflow MUST use only the Python standard library, so the track's tests run in CI and on the light path alike.
- **FR-033**: The repository MUST keep starter files (for learners to complete) separate from reference solutions; CI tests the solutions, and learners can point the same tests at the starter.

**Evidence and acceptance**

- **FR-034**: Each module MUST end with an evidence checklist (`contracts/evidence-checklist.md`) whose items can each be checked from a file, a command output or a link.
- **FR-035**: Every command and code example in the track MUST be run in a clean environment on Windows, macOS and Linux before release, and the date and tool versions recorded on the page.

### Key Entities

- **Verifier result**: the outcome of one verification (PASS, FAIL or UNVERIFIED), its exit code, its reason, the test counts from the report, the command, the time taken and where its evidence is.
- **Workflow record**: one task's ID, state, attempts used and allowed, verify command, last verifier result and its transition history.
- **Transition**: one change of state, with its sequence number, time, actor (person, agent or verifier), event, from-state, to-state, attempt number and optional note.
- **Regression patch**: a patch file that introduces the Module 6 bug in a disposable worktree.
- **Evidence bundle**: the files a learner keeps for a module: verifier results, run output, test reports, diff, workflow records, pull-request and CI links, review notes and reflection answers.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Clean-environment learner acceptance: at least three testers who did not write the track (at least one each on Windows, macOS and Linux), each on a fresh user account with only Git, `uv`, the GitHub CLI and a coding agent installed, complete Modules 6–8 from the pages alone, with 0 blocking problems left open and every step's stated expected result observed.
- **SC-002**: In that acceptance test, the median time for each module falls inside its stated range (45–60, 60–75 and 60–90 minutes); any module outside it has its estimate or content changed before release.
- **SC-003**: The light environment for Modules 6 and 7 holds no more than 10 packages, none of them PyTorch, and the baseline command finishes in under 2 minutes on a normal connection the first time.
- **SC-004**: The verifier's tests cover every row of its decision table (100%), and in Module 6 each tester gets exactly one PASS (exit 0), one FAIL (exit 1, naming the one failing test) and one UNVERIFIED (exit 2).
- **SC-005**: The workflow's tests classify all 56 state-event pairs (7 states × 8 events) as allowed or rejected, and both reference traces (success with one repair; exhaustion after 3 attempts) are reproduced by every tester.
- **SC-006**: In acceptance, 0 issues or pull requests reach the upstream repository, every tester's pull request shows the fork's existing Python and Flutter checks, and 0 merges happen without a person.
- **SC-007**: After the feature merges, the diff against the previous `main` for `src/`, `app/`, `docs/inference-contract.md`, `.claude/` and `.github/` is empty, and CI is green.
- **SC-008**: CI collects the track's tests (the collected count rises by the number of new tests) and executes 0 patched modules; adding a `.py` file to the patch folder makes CI fail.
- **SC-009**: The diff to `docs/workshop-setup.md` adds only the link paragraph and one file-table row; its three-hour core estimate is unchanged.
- **SC-010**: Every track page states that passing tests are not model accuracy or field suitability, and every page that names an agent tool lists it alphabetically with the no-endorsement note (checked page by page: 0 exceptions).

## Assumptions

- **Owner decision, 2026-10-26 (research R1)**: Module 6 uses the normalisation regression (mean/std subtraction added to `preprocess`), which `tests/test_infer.py` catches today, and refers back to Exercise 1 in one paragraph as "the same lesson, one level up: the contract, not the arithmetic". The alternative is the issue's `>=` to `>` change, framed as "the same bug class, now in real code". Both were checked to fail exactly one test.
- Learners have finished the core Modules 0–4 and Exercise 1, can use Git, a terminal and their agent's approvals, and have the `agents-practice` folder from Module 0.
- A free GitHub account and a public fork are enough for Module 8; branch rulesets on public repositories are available on the free plan, and the module still works where they are not.
- The GitHub facts in research R6 (Actions and Issues off on a new fork, the CLI's default target, no secrets on forks) are re-checked on the date the pages are written, because hosted tools change.
- The Stop hook is a Claude Code hook; other agents do not run it. The track says so and makes no promise that hooks work the same across agents.
- Slides are out of scope; they are updated in a separate change after the module content is approved.
- Times are estimates until the acceptance test measures them (SC-002).
- The track is in English, like the core course.
