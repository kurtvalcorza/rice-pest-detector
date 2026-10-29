# Module 6. Engineer: protect the inference contract (about 45–60 minutes)

In this module you break the real detector on purpose, in a throwaway copy of the repository, and watch which controls notice. One test catches the break. The repository's Stop hook does not. Then you build a small verifier that says PASS only when the tests really ran and really passed, and you make it say PASS, FAIL and UNVERIFIED.

**Passing tests show that the code does what its written contract says. They do not show that the model is accurate, validated in the field or suitable for decisions about crops.** Testing a machine-learning system covers more than its code: the data, the learning program and properties such as correctness and robustness each need checks of their own ([Zhang et al., 2022](https://doi.org/10.1109/TSE.2019.2962027)). This repository is a teaching demo; nothing here has been validated in the field.

## Before you start

This is the first module of the optional [advanced track](README.md). **You need** the core course (Modules 0–4 and Exercise 1 in [workshop-setup.md](../workshop-setup.md)), your clone of this repository, your `agents-practice` folder from Module 0, and the tools from [setup.md](../setup.md): [Git](../setup.md#git), [`uv`](../setup.md#uv-and-spec-kit) and [a coding agent](../setup.md#an-ai-coding-agent). You do not need PyTorch, Flutter, an emulator or model weights. The first `uv` command below needs the network once, to fetch Python 3.12, NumPy, Pillow and pytest; after that it works from `uv`'s cache.

**Agents.** Any coding agent you are allowed to use works. Where this page names agents, it names them only as examples, in alphabetical order (for example Antigravity, Claude Code, Codex). Naming them is not a recommendation or an endorsement; see the note in [setup.md, "An AI coding agent"](../setup.md#an-ai-coding-agent).

**The commands** assume your practice folder sits next to your clone, like this:

```text
agents-practice/        your practice folder from Module 0
rice-pest-detector/     your clone
rpd-m6/                 the throwaway worktree you create in step 2 (removed in step 7)
```

If your practice folder is somewhere else, change `../agents-practice` in the commands. Run every command from the folder the step names. Where bash (macOS, Linux, Git Bash) and PowerShell (Windows) differ, both are given. Keep the quotes around `"--junitxml={junit}"`: PowerShell would otherwise read the braces as code.

**Tested with** `uv` 0.13.5 and Git on Windows 11 (PowerShell 7 and Git Bash), 27 October 2026. macOS and Linux runs are still to be recorded.

## What you will learn

- **The inference contract is the definition of correct.** [docs/inference-contract.md](../inference-contract.md) says how a photo becomes the model's input. Its "Normalisation" row says **None**: no mean or standard-deviation subtraction. Code that "improves" this is wrong, however common the improvement is elsewhere.
- **A regression** is a change that breaks something that used to work. Regression testing means retesting software after it has been changed ([Elbaum et al., 2000](https://doi.org/10.1145/347636.348910)); a regression test is one that fails when such a change breaks something.
- **Fail-open versus fail-closed.** A fail-open check lets work through when it cannot decide; a fail-closed check refuses. Security design has long favoured the second: base the decision on positive evidence, so that when in doubt the answer is no ("fail-safe defaults", [Saltzer & Schroeder, 1975](https://doi.org/10.1109/PROC.1975.9939)).
- **Three kinds of control.** Instructions (`AGENTS.md`, skills) ask the agent to behave; the model may skip them. A local hook runs in one agent's harness on one computer. Independent CI runs the tests where neither the agent nor you can skip them. Even strong models often miss explicit instructions ([Skripko, 2025](https://doi.org/10.48550/arXiv.2509.18420)), and text an agent reads can redirect it away from yours ([Greshake et al., 2023](https://doi.org/10.1145/3605764.3623985)). Only a control that checks the thing you care about protects it.
- **Evidence, not claims.** An agent saying "all tests pass" is a claim. A fresh test report saying how many tests ran and how many failed is evidence. Research on coding agents shows why the difference matters: a test an agent writes for its own patch accepts many incorrect patches ([Mohsin et al., 2026](https://doi.org/10.48550/arXiv.2610.03984)), and patches that pass a benchmark's tests can still behave differently from the developer's own fix ([Wang et al., 2026](https://doi.org/10.1145/3744916.3764576)).

## Step 1. Baseline: the tests pass (5 minutes)

From your clone:

```bash
uv run --no-project --python 3.12 --with numpy==2.5.4 --with pillow==13.0.0 --with pytest --with-editable . python -m pytest tests/test_infer.py
```

**Expected:** `4 passed`. This installs only NumPy and Pillow (at the versions the repository pins), pytest and the package itself, about nine packages, with no PyTorch. `--no-project` stops `uv` writing a lock file into your clone; `--with-editable .` makes the package importable and makes any edit to it visible at once.

These four tests in [`tests/test_infer.py`](../../tests/test_infer.py) guard the reference implementation of the contract, [`src/rice_pest_detector/infer.py`](../../src/rice_pest_detector/infer.py). The first one, `test_preprocess_shape_range_and_no_normalisation`, feeds a pure red image through `preprocess` and checks that the red channel comes out as exactly 1.0 and the green as exactly 0.0.

## Step 2. Make a throwaway worktree and break the code (5 minutes)

A Git worktree is a second working folder for the same repository, on its own branch. Whatever you break there stays out of your clone, and one command removes it. From your clone:

```bash
mkdir -p ../agents-practice/advanced-evidence/m6
git worktree add ../rpd-m6 -b m6-practice
cd ../rpd-m6
```

```powershell
New-Item -ItemType Directory -Force ../agents-practice/advanced-evidence/m6 | Out-Null
git worktree add ../rpd-m6 -b m6-practice
cd ../rpd-m6
```

Now record a baseline with the reference verifier (you will build your own in step 5; for now, just see what it says):

```bash
uv run --no-project --python 3.12 python workshop/advanced/solutions/verify.py --evidence ../agents-practice/advanced-evidence/m6/baseline --min-tests 4 -- uv run --no-project --python 3.12 --with numpy==2.5.4 --with pillow==13.0.0 --with pytest --with-editable . python -m pytest tests/test_infer.py "--junitxml={junit}"
```

The command is the same in PowerShell. **Expected:** the test output, then a last line like `RESULT: PASS (4 tests ran, 0 failed) evidence=../agents-practice/advanced-evidence/m6/baseline`.

Then apply the regression and keep its diff:

```bash
git apply workshop/advanced/patches/m6-normalisation.patch
git diff --output=../agents-practice/advanced-evidence/m6/regression.diff
git diff --stat
```

**Expected:** `src/rice_pest_detector/infer.py | 1 +`. The patch adds one line to `preprocess`: it subtracts the ImageNet mean and divides by its standard deviation, a step many image models expect. This model's image processor does not (`do_normalize: false`, in the inference contract's "Normalisation" row). An agent asked to "tidy up the preprocessing" could well add the same line. The contract says not to.

**Check you are in the right place.** `git worktree list` shows two folders; `git status` in `../rice-pest-detector` must be clean. If the patch landed in your clone by mistake, run `git restore src/rice_pest_detector/infer.py` there.

## Step 3. See the right test fail (5 minutes)

In the worktree:

```bash
uv run --no-project --python 3.12 --with numpy==2.5.4 --with pillow==13.0.0 --with pytest --with-editable . python -m pytest tests/test_infer.py
```

**Expected:** `1 failed, 3 passed`, and the failure is `test_preprocess_shape_range_and_no_normalisation`. The other three tests still pass: the shape, the type, greyscale and RGBA input, the model input size and the postprocessing are all fine. Only the line of the contract that says "no normalisation" is broken, and only one test guards it.

**Exercise 1, one level up.** In Exercise 1, `test_exactly_100_has_no_discount` was the one test that stopped `total > 100` becoming `total >= 100`; without it, six tests still passed. Here it is the same lesson, one level up: the contract, not the arithmetic. A test pins a line of a written contract, and an agent following common practice would "fix" that line.

## Step 4. Read and run the Stop hook (10 minutes)

Open [`.claude/hooks/require_green_tests.py`](../../.claude/hooks/require_green_tests.py). It is a Claude Code Stop hook: when that agent tries to finish, the hook runs `flutter test` in `app/` and blocks the first attempt while those tests fail. Other agents do not run it.

Run it by hand in the patched worktree:

```bash
uv run --no-project --python 3.12 python .claude/hooks/require_green_tests.py > ../agents-practice/advanced-evidence/m6/stop-hook.txt 2>&1; echo "exit $?"
cat ../agents-practice/advanced-evidence/m6/stop-hook.txt
```

```powershell
uv run --no-project --python 3.12 python .claude/hooks/require_green_tests.py *> ../agents-practice/advanced-evidence/m6/stop-hook.txt; "exit $LASTEXITCODE"
Get-Content ../agents-practice/advanced-evidence/m6/stop-hook.txt
```

**Expected without Flutter:** `exit 0` and `Warning: could not run flutter test, so the stop is allowed. Details: flutter not found on PATH`. **With Flutter installed:** after a few minutes, `exit 0` and `App tests pass.` Either way the stop is allowed, with the regression in place.

Why: the hook runs `flutter test`, never `pytest`, and the app's tests check the app against fixtures already committed to the repository; nothing in them calls `preprocess` in `infer.py`. The hook cannot see this change. It also lets the agent stop in three cases on purpose, so that it never traps an agent in a loop:

1. it is switched off (`RICE_PEST_STOP_HOOK=off`);
2. Flutter is missing, or `flutter test` cannot run or times out;
3. it has already blocked once and the tests still fail.

That is fail-open by design, and the course page says so ("passing tests stay your responsibility"). A hook is a useful nudge for one agent on one computer; it is not the check that protects the contract. Here, the only thing that protects this line is `tests/test_infer.py`, run by you or by CI.

## Step 5. Build the verifier, test-first, with your agent (15–20 minutes)

The verifier runs a test command and answers with one of three results:

| Result | Exit code | Means |
| :-- | :-- | :-- |
| PASS | 0 | The command exited 0 **and** a fresh test report shows at least the required number of tests ran, none failed |
| FAIL | 1 | The report shows a failure or error: the tests ran and said no. Worth repairing |
| UNVERIFIED | 2 | Anything else: the command was not found, timed out, wrote no report, ran 0 tests, skipped them all, or ran too few. Stop and look |

The full decision table is in [specs/004-advanced-workshop/contracts/verifier-cli.md](../../specs/004-advanced-workshop/contracts/verifier-cli.md). The starter, [`workshop/advanced/starter/verify.py`](../../workshop/advanced/starter/verify.py), has the functions and their docstrings, with `TODO` bodies. The tests in [`workshop/advanced/tests/`](../../workshop/advanced/tests/) are the specification. Point them at the starter and watch them fail:

```bash
RPD_WORKSHOP_IMPL=starter uv run --no-project --python 3.12 --with pytest python -m pytest workshop/advanced/tests
```

```powershell
$env:RPD_WORKSHOP_IMPL="starter"; uv run --no-project --python 3.12 --with pytest python -m pytest workshop/advanced/tests
```

**Expected:** about 40 failures, each with `NotImplementedError`; the safety tests pass. Now hand the work to your agent, in the worktree. A prompt that works:

> Read specs/004-advanced-workshop/contracts/verifier-cli.md and workshop/advanced/starter/verify.py. Fill in the starter so that the tests in workshop/advanced/tests pass when run with RPD_WORKSHOP_IMPL=starter. Use only the Python standard library and never use a shell to run the command. Do not change any test, anything under src/, or the solutions folder. Work one function at a time, starting with read_report, and run the tests after each one. Show me the plan first and wait for my approval.

Read each diff before you approve it. If the agent edits a test, `infer.py` or the reference solution, say no: the regression in `infer.py` is there on purpose.

**Check the agent's scope before you keep its work.** The prompt asks the agent to stay inside the starter, but that is an instruction, and the model may not follow it. This check does not depend on the agent. In the worktree:

```bash
git status --short > ../agents-practice/advanced-evidence/m6/scope.txt
git diff --stat -- src tests workshop/advanced/tests workshop/advanced/solutions >> ../agents-practice/advanced-evidence/m6/scope.txt
cat ../agents-practice/advanced-evidence/m6/scope.txt
```

The commands are the same in PowerShell.

**Expected:** the file lists exactly two changed files, ` M src/rice_pest_detector/infer.py` (your regression) and ` M workshop/advanced/starter/verify.py`, then a summary showing only `src/rice_pest_detector/infer.py | 1 +`. Anything more means the agent went outside the task. Look at it with `git diff`, undo changed files with `git restore <file>` and new ones with `git clean -n` then `git clean -f <file>`. If `infer.py` shows more than one changed line, run `git restore src/rice_pest_detector/infer.py` and apply the patch again.

When the tests pass with `RPD_WORKSHOP_IMPL=starter` and the scope check is clean, copy your verifier out of the worktree so you keep it:

```bash
cp workshop/advanced/starter/verify.py ../agents-practice/advanced-evidence/m6/my-verify.py
unset RPD_WORKSHOP_IMPL
```

```powershell
Copy-Item workshop/advanced/starter/verify.py ../agents-practice/advanced-evidence/m6/my-verify.py
Remove-Item Env:RPD_WORKSHOP_IMPL
```

Short of time? Read the reference, [`workshop/advanced/solutions/verify.py`](../../workshop/advanced/solutions/verify.py), and use it in step 6.

## Step 6. Make it say FAIL, UNVERIFIED and PASS (10 minutes)

Use your verifier (`workshop/advanced/starter/verify.py`) if its tests pass, or the reference (`workshop/advanced/solutions/verify.py`). The commands below use the reference. All three run in the worktree; each command is the same in PowerShell.

**FAIL, with the regression in place:**

```bash
uv run --no-project --python 3.12 python workshop/advanced/solutions/verify.py --evidence ../agents-practice/advanced-evidence/m6/regression --min-tests 4 -- uv run --no-project --python 3.12 --with numpy==2.5.4 --with pillow==13.0.0 --with pytest --with-editable . python -m pytest tests/test_infer.py "--junitxml={junit}"
```

**Expected:** exit code 1 and `RESULT: FAIL (1 of 4 tests failed: tests.test_infer::test_preprocess_shape_range_and_no_normalisation) evidence=...`.

**UNVERIFIED, with a test runner that does not exist** (a misspelt command stands in for a broken environment):

```bash
uv run --no-project --python 3.12 python workshop/advanced/solutions/verify.py --evidence ../agents-practice/advanced-evidence/m6/unavailable --min-tests 4 -- no-such-runner tests/test_infer.py "--junitxml={junit}"
```

**Expected:** exit code 2 and `RESULT: UNVERIFIED (command not found: no-such-runner) evidence=...`. The Stop hook treats "could not run" as "allow"; the verifier treats it as "not verified".

**PASS, after restoring the code:**

```bash
git restore src/rice_pest_detector/infer.py
uv run --no-project --python 3.12 python workshop/advanced/solutions/verify.py --evidence ../agents-practice/advanced-evidence/m6/restored --min-tests 4 -- uv run --no-project --python 3.12 --with numpy==2.5.4 --with pillow==13.0.0 --with pytest --with-editable . python -m pytest tests/test_infer.py "--junitxml={junit}"
```

**Expected:** exit code 0 and `RESULT: PASS (4 tests ran, 0 failed) evidence=...`. To see an exit code: `echo $?` in bash, `$LASTEXITCODE` in PowerShell.

The last lines of a real walk through this page (Windows 11, 27 October 2026, in a folder whose path contains a space; on Windows the evidence path is printed with backslashes):

```text
RESULT: PASS (4 tests ran, 0 failed) evidence=..\agents-practice\advanced-evidence\m6\baseline
RESULT: FAIL (1 of 4 tests failed: tests.test_infer::test_preprocess_shape_range_and_no_normalisation) evidence=..\agents-practice\advanced-evidence\m6\regression
RESULT: UNVERIFIED (command not found: no-such-runner) evidence=..\agents-practice\advanced-evidence\m6\unavailable
RESULT: PASS (4 tests ran, 0 failed) evidence=..\agents-practice\advanced-evidence\m6\restored
```

Each run left `verification.json`, `run.log` and `junit.xml` in its evidence folder. Open one: you can check the result without trusting anyone's account of it, the agent's included.

## Step 7. Clean up (5 minutes)

From your clone:

```bash
cd ../rice-pest-detector
git worktree remove --force ../rpd-m6
git branch -D m6-practice
git worktree list
git status
```

**Expected:** `git worktree list` shows only your clone, and `git status` is clean. Your evidence is still in `../agents-practice/advanced-evidence/m6/`. Check it against the [evidence checklist](evidence-checklist.md#module-6-engineer), and write your answers to the reflection questions below into `reflection.md` there.

## If something does not work

- **`uv` cannot download Python or packages.** The first run needs the network. Connect once; later runs use the cache.
- **`error: patch failed` or `does not apply`.** The patch is applied in the worktree, once. If `git diff --stat` already shows the change, it is applied. If `infer.py` changed since the patch was made, the track's own test in CI fails first; tell us (see [Getting help](../workshop-setup.md#getting-help)).
- **The patch ended up in your clone.** Run `git restore src/rice_pest_detector/infer.py` in the clone, then go back to the worktree.
- **A path with spaces breaks a command.** Quote it (`"../my practice/advanced-evidence/m6"`). The verifier runs the command without a shell, so quoting is up to your terminal.
- **PowerShell says something about a script block.** Put `"--junitxml={junit}"` in double quotes.
- **`RESULT: UNVERIFIED (... fewer than the 4 required)`.** A test was deselected, renamed, skipped or deleted. Run the test command on its own and count.
- **`git worktree remove` refuses.** Use `--force` as shown; the worktree holds nothing you need once the evidence is copied out.

## Reflection

Write your answers in `reflection.md`, then compare.

<details>
<summary>1. Which control would have caught this regression: the instructions in AGENTS.md, the Stop hook, or CI? Why?</summary>

CI, because it runs `python -m pytest` on every pull request to `main` and that includes `tests/test_infer.py`. The Stop hook runs `flutter test`, which never calls `preprocess`, and it allows the stop anyway when Flutter is missing. Instructions can ask an agent to keep the contract, but the model may not follow them. Running the test yourself also catches it; the point is that something must run the right test.
</details>

<details>
<summary>2. What does <code>--min-tests 4</code> protect against?</summary>

A run that passes because fewer tests ran: a test deselected with `-k`, renamed so it is no longer collected, skipped, or deleted by an agent that wanted the failure gone. Exit code 0 and "0 failed" look the same whether 4 tests ran or 3. With the count pinned, 3 is UNVERIFIED.
</details>

<details>
<summary>3. An agent "fixes" the failure by deleting the red-image test and adding a new, weaker test, so four tests still run. What does the verifier say, and what catches it?</summary>

PASS: four tests ran and none failed. The verifier checks that tests ran and passed, not that they are the right tests. Reading the diff catches it (a change under `tests/` when the task was about `src/`), and so does a review rule that changes to tests need a person's approval. A control protects only what it checks.
</details>

<details>
<summary>4. Why is UNVERIFIED a separate result from FAIL?</summary>

FAIL means the tests ran and said no, which is worth repairing. UNVERIFIED means nothing trustworthy happened: the runner is missing, it timed out, or the report is gone. Repairing code will not fix that; a person needs to look. Module 7 uses exactly this difference to decide between "repair" and "blocked".
</details>

<details>
<summary>5. The verifier says PASS. Does that mean the detector works on rice fields?</summary>

No. It means `infer.py` still does what the inference contract says. Whether the model counts insects well on new photos is a separate question, answered (so far only partly) by the evaluation record, and no model here has been validated in the field.
</details>

## References

Elbaum, S., Malishevsky, A. G., & Rothermel, G. (2000). Prioritizing test cases for regression testing. *ACM SIGSOFT Software Engineering Notes*, 25(5), 102–112. https://doi.org/10.1145/347636.348910

Greshake, K., Abdelnabi, S., Mishra, S., Endres, C., Holz, T., & Fritz, M. (2023). Not what you've signed up for: Compromising real-world LLM-integrated applications with indirect prompt injection. In *Proceedings of the 16th ACM Workshop on Artificial Intelligence and Security* (pp. 79–90). https://doi.org/10.1145/3605764.3623985

Mohsin, M. A., Kim, M., Ruan, K., Garg, S., Kumar, V., & Ramanathan, M. K. (2026). *Teaching agents to code reliably* (arXiv:2610.03984). arXiv. https://doi.org/10.48550/arXiv.2610.03984

Saltzer, J. H., & Schroeder, M. D. (1975). The protection of information in computer systems. *Proceedings of the IEEE*, 63(9), 1278–1308. https://doi.org/10.1109/PROC.1975.9939

Skripko, N. (2025). *Instruction-following evaluation in function calling for large language models* (arXiv:2509.18420). arXiv. https://doi.org/10.48550/arXiv.2509.18420

Wang, Y., Pradel, M., & Liu, Z. (2026). Are "solved issues" in SWE-bench really solved correctly? An empirical study. In *Proceedings of the IEEE/ACM 48th International Conference on Software Engineering* (pp. 169–181). https://doi.org/10.1145/3744916.3764576

Zhang, J. M., Harman, M., Ma, L., & Liu, Y. (2022). Machine learning testing: Survey, landscapes and horizons. *IEEE Transactions on Software Engineering*, 48(1), 1–36. https://doi.org/10.1109/TSE.2019.2962027
