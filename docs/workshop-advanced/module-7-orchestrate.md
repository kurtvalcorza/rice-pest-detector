# Module 7. Orchestrate: a bounded agent loop (about 60–75 minutes)

In Module 6 you built a verifier. In this module it becomes a gate. You run the same regression through a small state machine where an agent can say it is done, but only the verifier's exit code moves the work forward, repairs stop after three attempts, and nothing is approved without a person. Then you turn the question around: the tests passed, but could they have failed? You plant one bug per requirement, and find that four of the six get past Module 6's tests.

**Passing tests show that the code does what its written contract says. They do not show that the model is accurate, validated in the field or suitable for decisions about crops.** This repository is a teaching demo; nothing here has been validated in the field.

## Before you start

This is the second module of the optional [advanced track](README.md). **You need** to have finished [Module 6](module-6-engineer.md), and the same tools: [Git](../setup.md#git), [`uv`](../setup.md#uv-and-spec-kit) and [a coding agent](../setup.md#an-ai-coding-agent). You do not need PyTorch, Flutter, an emulator, model weights or a GitHub account.

**Agents.** Any coding agent you are allowed to use works. Where this page names agents, it names them only as examples, in alphabetical order (for example Antigravity, Claude Code, Codex). Naming them is not a recommendation or an endorsement; see the note in [setup.md, "An AI coding agent"](../setup.md#an-ai-coding-agent).

**The commands** assume the same folders as Module 6, with a new throwaway worktree:

```text
agents-practice/        your practice folder from Module 0
rice-pest-detector/     your clone
rpd-m7/                 the throwaway worktree you create in step 1 (removed in step 8)
```

Where bash (macOS, Linux, Git Bash) and PowerShell (Windows) differ, both are given. Keep the quotes around `"--junitxml={junit}"`.

**Tested with** Git Bash and PowerShell 7 on Windows 11, in a folder whose path contains a space, 7 November 2026. On Linux (Ubuntu under WSL) the track's tests and step 6 were run; a full Linux walk and macOS are still to be recorded.

## What you will learn

- **A state machine** is a fixed set of states and the only moves allowed between them. Written as a table, it can be read, tested in full and argued with. Anything not in the table is refused.
- **A bounded loop.** An agent left to retry can retry for ever, and can stop trying the right thing. A limit turns "keep going" into a decision a person makes.
- **Evidence-driven transitions.** The agent may say "done". That moves the task to `verifying`, and no further. Only a verifier run moves it on.
- **A human gate.** A person approves, and the record names who. Module 8 moves this gate somewhere an agent cannot reach.
- **Mutation testing** checks the tests themselves: plant a small bug and see whether a test fails. If none does, the tests could not have caught that bug ([DeMillo et al., 1978](https://doi.org/10.1109/C-M.1978.218136); [Jia & Harman, 2011](https://doi.org/10.1109/TSE.2010.62)).
- **Checked, unguarded, assumed.** Three honest labels for a requirement. `checked`: a planted bug was caught. `unguarded`: a planted bug got through. `assumed`: nothing here tests it, and a person accepts it. A label comes from a run or a stated acceptance, never from anyone's account.

Those last two ideas also sit at the centre of Proof-Driven Development, Microsoft Research's approach of checking agent-written code against an approved specification, which inspired this part of the module ([Lavaee & Philipose](https://www.microsoft.com/en-us/research/blog/formally-verifying-agent-written-full-stack-web-apps-with-pdd-kit/)). That work uses formal proof in Rust, which holds for every input. **What you do here is testing, not proof.** A caught bug shows that one planted bug was caught, and nothing more.

## Step 1. Make a throwaway worktree (5 minutes)

From your clone:

```bash
mkdir -p ../agents-practice/advanced-evidence/m7
git worktree add ../rpd-m7 -b m7-practice
cd ../rpd-m7
W() { uv run --no-project --python 3.12 python workshop/advanced/solutions/workflow.py --state-dir ../agents-practice/advanced-evidence/m7/records "$@"; }
```

```powershell
New-Item -ItemType Directory -Force ../agents-practice/advanced-evidence/m7 | Out-Null
git worktree add ../rpd-m7 -b m7-practice
cd ../rpd-m7
function W { uv run --no-project --python 3.12 python workshop/advanced/solutions/workflow.py --state-dir ../agents-practice/advanced-evidence/m7/records @args }
```

`W` saves typing for the `event`, `verify` and `show` commands. Keep this terminal open, or define it again. **Expected:** `git worktree list` shows two folders.

## Step 2. Build the workflow, test-first, with your agent (15–20 minutes)

The states and the only allowed moves:

| From | Event | Who | To |
| :-- | :-- | :-- | :-- |
| `planning` | `plan_accepted` | a person | `implementing` |
| `implementing` | `implementation_done` | the agent | `verifying` |
| `verifying` | `verifier_pass` | the verifier | `awaiting_approval` |
| `verifying` | `verifier_fail`, attempts left | the verifier | `repairing` |
| `verifying` | `verifier_fail`, last attempt | the verifier | `blocked` (retry exhausted) |
| `verifying` | `verifier_unverified` | the verifier | `blocked` (verification unavailable) |
| `repairing` | `repair_done` | the agent | `verifying` |
| `awaiting_approval` | `approve` | a person | `approved` |
| `awaiting_approval` | `reject` | a person | `blocked` (rejected by a person) |

Everything else is refused. Exit 0 from the verifier is a pass, exit 1 a failure worth repairing, and anything else is unverified. That is why Module 6 kept FAIL and UNVERIFIED apart: repairing code cannot fix a missing test runner, so the task stops. The full contract is [specs/004-advanced-workshop/contracts/workflow-cli.md](../../specs/004-advanced-workshop/contracts/workflow-cli.md).

The starter, [`workshop/advanced/starter/workflow.py`](../../workshop/advanced/starter/workflow.py), has this table as data with four rows left as `TODO`, and functions with `TODO` bodies. Point the tests at it:

```bash
RPD_WORKSHOP_IMPL=starter uv run --no-project --python 3.12 --with pytest python -m pytest workshop/advanced/tests -k workflow
```

```powershell
$env:RPD_WORKSHOP_IMPL="starter"; uv run --no-project --python 3.12 --with pytest python -m pytest workshop/advanced/tests -k workflow
```

**Expected:** about 220 failures and errors, from `NotImplementedError` in the starter. Now hand it to your agent, in the worktree, and keep the prompt in `../agents-practice/advanced-evidence/m7/prompts.md`:

> Read specs/004-advanced-workshop/contracts/workflow-cli.md and workshop/advanced/starter/workflow.py. Fill in the starter so that the tests selected by `-k workflow` in workshop/advanced/tests pass with RPD_WORKSHOP_IMPL=starter. Use only the Python standard library. Do not change any test, anything under src/, or the solutions folder. Start with the four TODO rows of the transition table and explain each choice. Show me the plan first and wait for my approval.

Read each diff before you approve it. The four rows are the lesson: why does `verifier_unverified` never go to `repairing`? Then check the scope, as in Module 6:

```bash
git status --short
```

**Expected:** one changed file, ` M workshop/advanced/starter/workflow.py`. Keep your work and clear the setting:

```bash
cp workshop/advanced/starter/workflow.py ../agents-practice/advanced-evidence/m7/my-workflow.py
git restore workshop/advanced/starter/workflow.py
unset RPD_WORKSHOP_IMPL
```

```powershell
Copy-Item workshop/advanced/starter/workflow.py ../agents-practice/advanced-evidence/m7/my-workflow.py
git restore workshop/advanced/starter/workflow.py
Remove-Item Env:RPD_WORKSHOP_IMPL
```

The steps below use the reference, so that everyone's output matches. Short of time? Read [`workshop/advanced/solutions/workflow.py`](../../workshop/advanced/solutions/workflow.py) and carry on.

## Step 3. A task that fails, is repaired and is approved (10 minutes)

Start a task. The verify command is stored in the record, so nobody can change it later by typing a different one. This command is the same in both shells:

```bash
uv run --no-project --python 3.12 python workshop/advanced/solutions/workflow.py --state-dir ../agents-practice/advanced-evidence/m7/records start m7-success -- uv run --no-project --python 3.12 python workshop/advanced/solutions/verify.py --evidence ../agents-practice/advanced-evidence/m7/success --min-tests 4 -- uv run --no-project --python 3.12 --with numpy==2.5.4 --with pillow==13.0.0 --with pytest --with-editable . python -m pytest tests/test_infer.py "--junitxml={junit}"
```

Write `start` out in full, as here: a PowerShell function drops the first `--` it is given, so `W start` would fail there.

You accept the plan. The Module 6 patch stands in for the agent's first attempt at "tidying the preprocessing". The agent says it is done:

```bash
W event m7-success plan_accepted
git apply workshop/advanced/patches/m6-normalisation.patch
W event m7-success implementation_done --actor agent
W verify m7-success
```

**Expected:** after the test output,

```text
RESULT: FAIL (1 of 4 tests failed: tests.test_infer::test_preprocess_shape_range_and_no_normalisation) evidence=..\agents-practice\advanced-evidence\m7\success
m7-success: verifying -> repairing (attempt 1 of 3)
```

The agent said it was done; the verifier disagreed, and the verifier decides. Now a real handoff. Give your agent this prompt, and add it to `prompts.md`:

> The tests in tests/test_infer.py fail. Read docs/inference-contract.md and fix src/rice_pest_detector/infer.py to match it. Change nothing else, and do not edit any test. Show me the diff.

Read the diff. **Expected:** `git diff --stat` shows nothing, because the agent removed the added line. If it changed anything else, undo that with `git restore src/rice_pest_detector/infer.py`. Then record the handoff, verify and approve:

```bash
W event m7-success repair_done --actor agent
W verify m7-success
W event m7-success approve --note "diff read: infer.py is back to the original"
W show m7-success
```

**Expected:**

```text
task:     m7-success
state:    approved
attempts: 2 of 3
last verification: PASS, exit 0: 4 tests ran, 0 failed

seq  at                    actor     event                from               to                 attempt  result  note
1    2026-11-06T17:15:24Z  human     plan_accepted        planning           implementing
2    2026-11-06T17:15:25Z  agent     implementation_done  implementing       verifying
3    2026-11-06T17:15:41Z  verifier  verifier_fail        verifying          repairing          1        FAIL
4    2026-11-06T17:15:41Z  agent     repair_done          repairing          verifying
5    2026-11-06T17:15:45Z  verifier  verifier_pass        verifying          awaiting_approval  2        PASS
6    2026-11-06T17:15:45Z  human     approve              awaiting_approval  approved                            diff read: infer.py is back to the original
```

The record is in `../agents-practice/advanced-evidence/m7/records/m7-success.json`. Open it. A reference copy is in [`workshop/advanced/solutions/traces/`](../../workshop/advanced/solutions/traces/).

## Step 4. A task that runs out of attempts (5 minutes)

Now an agent that keeps claiming a repair it has not made. Start a second task, the same command with a new name and evidence folder:

```bash
uv run --no-project --python 3.12 python workshop/advanced/solutions/workflow.py --state-dir ../agents-practice/advanced-evidence/m7/records start m7-exhaustion -- uv run --no-project --python 3.12 python workshop/advanced/solutions/verify.py --evidence ../agents-practice/advanced-evidence/m7/exhaustion --min-tests 4 -- uv run --no-project --python 3.12 --with numpy==2.5.4 --with pillow==13.0.0 --with pytest --with-editable . python -m pytest tests/test_infer.py "--junitxml={junit}"
```

```bash
W event m7-exhaustion plan_accepted
git apply workshop/advanced/patches/m6-normalisation.patch
W event m7-exhaustion implementation_done --actor agent
W verify m7-exhaustion
W event m7-exhaustion repair_done --actor agent
W verify m7-exhaustion
W event m7-exhaustion repair_done --actor agent
W verify m7-exhaustion
W show m7-exhaustion
```

**Expected:** the last `verify` prints `m7-exhaustion: verifying -> blocked (attempt 3 of 3)`, and `show` starts:

```text
task:     m7-exhaustion
state:    blocked (retry_exhausted)
attempts: 3 of 3
last verification: FAIL, exit 1: 1 of 4 tests failed: tests.test_infer::test_preprocess_shape_range_and_no_normalisation
```

`W verify` exits 0 here, because the workflow did its job: the task ending blocked is a result, not an error. Leave the patch in place for the next step.

## Step 5. Try to cheat (5 minutes)

`blocked` is final, and so is `approved`. Try to carry on, and try the moves the table does not allow. To see an exit code: `echo $?` in bash, `$LASTEXITCODE` in PowerShell.

```bash
W event m7-exhaustion repair_done --actor agent
W event m7-exhaustion verifier_pass
W event m7-exhaustion approve --actor agent
```

**Expected:** each exits 3 and changes nothing. The first says `refused: repair_done is not allowed in blocked; allowed here: nothing: it is finished`. The second says ``refused: verifier_pass cannot be sent by hand: run `workflow.py verify m7-exhaustion` ``. In a task waiting for approval, `approve --actor agent` gets `refused: approve in awaiting_approval needs a person, not actor agent`. Put one of these refusals, with its exit code, in `refused.txt` in your evidence folder.

These are real limits, but know what they cost to get around. The record is a local file, and `--actor human` is a word anyone can type: an agent that can write to your disk could edit the record, or call itself human. The workflow makes the process visible and bounded. It does not stop a tool with write access from lying. Module 8 moves approval to a pull-request review, which an agent cannot give itself.

Now remove the bug, ready for the last part:

```bash
git restore src/rice_pest_detector/infer.py
git status --short
```

**Expected:** no output: the tree is clean.

## Step 6. Could the tests have failed? (10 minutes)

The verifier told you the tests passed. It cannot tell you whether they would have noticed a break. In Module 6 one test guarded one line, but how much of the contract is guarded like that? [`workshop/advanced/mutants.json`](../../workshop/advanced/mutants.json) lists six requirements of the inference contract, each with a patch that breaks it. The mutation check plants each bug in turn, runs your verifier, and removes the bug. It refuses to run in your main clone, or on a tree with changes. Run it with Module 6's four tests:

```bash
uv run --no-project --python 3.12 python workshop/advanced/solutions/mutation_check.py --mutants workshop/advanced/mutants.json --evidence ../agents-practice/advanced-evidence/m7/mutation-m6 -- uv run --no-project --python 3.12 python workshop/advanced/solutions/verify.py --evidence ../agents-practice/advanced-evidence/m7/mutation-m6/run --min-tests 4 -- uv run --no-project --python 3.12 --with numpy==2.5.4 --with pillow==13.0.0 --with pytest --with-editable . python -m pytest tests/test_infer.py "--junitxml={junit}"
```

**Expected** (about 20 seconds, exit 1):

```text
baseline    PASS (4 tests ran, 0 failed)
unguarded   orientation (verifier exit 0: 4 tests ran, 0 failed)
checked     no-normalisation (verifier exit 1: 1 of 4 tests failed: tests.test_infer::test_preprocess_shape_range_and_no_normalisation)
unguarded   resize-filter (verifier exit 0: 4 tests ran, 0 failed)
checked     inclusive-threshold (verifier exit 1: 1 of 4 tests failed: tests.test_infer::test_postprocess_threshold_is_inclusive_and_scales_boxes)
unguarded   sorted-by-score (verifier exit 0: 4 tests ran, 0 failed)
unguarded   default-threshold (verifier exit 0: 4 tests ran, 0 failed)
RESULT: 2 checked, 4 unguarded, 0 unverified (a caught bug is testing, not proof) report=..\agents-practice\advanced-evidence\m7\mutation-m6\mutation-report.json
```

Stop and take that in. Every run of Module 6 said PASS, honestly: four tests ran and passed. Yet you could stop the code applying EXIF rotation, change the resize filter, drop the sort or move the default threshold, and those four tests would still pass.

This was real, not staged. When this module was written, those four bugs got past every Python test touching this code, not only these four. The repository closed the gap with [`tests/test_infer_contract.py`](../../tests/test_infer_contract.py). Run the check with those tests added:

```bash
uv run --no-project --python 3.12 python workshop/advanced/solutions/mutation_check.py --mutants workshop/advanced/mutants.json --evidence ../agents-practice/advanced-evidence/m7/mutation-contract -- uv run --no-project --python 3.12 python workshop/advanced/solutions/verify.py --evidence ../agents-practice/advanced-evidence/m7/mutation-contract/run --min-tests 8 -- uv run --no-project --python 3.12 --with numpy==2.5.4 --with pillow==13.0.0 --with pytest --with-editable . python -m pytest tests/test_infer.py tests/test_infer_contract.py "--junitxml={junit}"
```

**Expected:** `RESULT: 6 checked, 0 unguarded, 0 unverified`, exit 0.

Read `mutation-report.json` in that folder, especially `assumed`: Pillow, NumPy, the trained weights, ONNX Runtime, the app's Dart port, and the list of requirements itself. Nothing here tests those; each is accepted, with a reason. Six out of six does not mean the contract is met for every photo. It means six planted bugs were caught, and a requirement nobody wrote down has no mutant, so this check cannot notice it.

## Step 7. Optional: a connected path (not needed, not tested in CI)

So far you have been the link between the agent and the workflow. A short script can do that, if your agent has a non-interactive command (for example `claude -p` or `codex exec`; check your tool's documentation). **This path is optional, connected, and not tested in CI.** It runs an agent with no person watching each step, so give that agent as few permissions as your tool allows, and use it only in a throwaway worktree. Save this outside the worktree as `../agents-practice/connected_loop.py`:

```python
"""Optional, connected, not tested in CI. Drives one task that is already in verifying."""
import json
import subprocess
import sys
from pathlib import Path

STATE_DIR = "../agents-practice/advanced-evidence/m7/records"
WORKFLOW = [sys.executable, "workshop/advanced/solutions/workflow.py", "--state-dir", STATE_DIR]
PROMPT = ("The tests in tests/test_infer.py fail. Read docs/inference-contract.md and fix "
          "src/rice_pest_detector/infer.py to match it. Change nothing else, and do not edit any test.")

task, agent = sys.argv[1], sys.argv[2:]  # agent: your agent's non-interactive command, without the prompt


def state():
    return json.loads(Path(STATE_DIR, f"{task}.json").read_text(encoding="utf-8"))["state"]


while state() == "verifying":
    subprocess.run([*WORKFLOW, "verify", task], check=True)
    if state() != "repairing":
        break
    subprocess.run([*agent, PROMPT], check=True)
    subprocess.run([*WORKFLOW, "event", task, "repair_done", "--actor", "agent"], check=True)
print(f"{task}: {state()}. A person decides what happens next.")
```

Start a new task as in step 3, and take it to `verifying` with the patch applied. Then run `uv run --no-project --python 3.12 python ../agents-practice/connected_loop.py <task> <your agent's command>`.

Notice what the script cannot do. The table still bounds it at three attempts. It stops at `awaiting_approval` or `blocked`, because it has no way to approve. The script was tested with a stand-in agent, not a real one, so yours may need its command adjusted.

## Step 8. Clean up (5 minutes)

From your clone:

```bash
cd ../rice-pest-detector
git worktree remove --force ../rpd-m7
git branch -D m7-practice
git worktree list
git status
```

**Expected:** `git worktree list` shows only your clone, and `git status` is clean. Your evidence is in `../agents-practice/advanced-evidence/m7/`. Check it against the [evidence checklist](evidence-checklist.md#module-7-orchestrate), and write your answers to the reflection questions below into `reflection.md` there.

## If something does not work

- **`usage error: unrecognized arguments` from `start`.** In PowerShell, `W start` loses its `--`. Write the `start` command out in full, as in step 3.
- **`W` is not found.** It lasts only as long as your terminal. Define it again, in the worktree.
- **`record problem: a record for ... already exists`.** Task names are single-use. Pick a new name, or delete that task's `.json` file in `records`.
- **`record problem` on a file you edited.** The workflow replays the history through the table each time it loads a record, and refuses a record that does not add up. Start a new task.
- **`NOT JUDGED (this is the main clone ...)`.** Run the mutation check from the worktree, not your clone.
- **`NOT JUDGED (the worktree is not clean ...)`.** Run `git status --short`. If a patch is still applied, run `git restore src/rice_pest_detector/infer.py`.
- **`NOT JUDGED (the baseline does not pass ...)`.** The check refuses to judge if the code fails before any bug is planted. Fix that first.
- **The mutation check was stopped part-way.** The worktree may still hold a planted bug. Delete the worktree and make a new one; do not try to repair it.
- **`does not apply`.** A patch is already in place. Run `git status --short` and restore the file.
- **A path with spaces breaks a command.** Quote it. The verifier and the workflow run commands without a shell, so quoting is up to your terminal.

## Reflection

Write your answers in `reflection.md`, then compare.

<details>
<summary>1. What moved each task forward, and what did not?</summary>

Out of `verifying`, only the verifier's exit code. The agent's `implementation_done` and `repair_done` moved a task to `verifying` and no further: in step 4 the agent claimed a repair twice, and neither claim got the task past the next run. A person's `plan_accepted` and `approve` moved the rest.
</details>

<details>
<summary>2. Why does UNVERIFIED block the task straight away, when FAIL gets three attempts?</summary>

FAIL means the tests ran and said no, so changing the code might help. UNVERIFIED means nothing trustworthy happened: a missing runner or a timeout. Asking the agent to change code cannot fix that, and an attempt spent there would only look like progress. A person needs to look.
</details>

<details>
<summary>3. What can the workflow not stop?</summary>

A tool with write access can edit or delete the record, or send `--actor human`. The record is a process control, not a tamper-proof one. It makes honest work visible and bounded. Replaying the history catches a careless edit; it does not catch a careful one. Module 8 uses a pull-request review, where the approval comes from a person's account.
</details>

<details>
<summary>4. Every Module 6 run said PASS, and the mutation check found four unguarded requirements. Was the verifier wrong?</summary>

No. It answered its own question correctly: the tests ran and passed. It cannot answer whether the tests could have failed for a given bug. That is a different question, and it needs a different check. A control protects only what it checks, and that includes the checks themselves.
</details>

<details>
<summary>5. The report says 6 checked. Is the contract proved?</summary>

No. Each `checked` means one planted bug was caught. A different bug in the same line might get through, and a requirement nobody wrote down has no mutant. Formal proof, such as the Verus proofs in Proof-Driven Development, covers every input; these tests do not. Nor do they say anything about the `assumed` list, which a person accepts.
</details>

<details>
<summary>6. An agent wants to delete a row from <code>mutants.json</code> so the report reads better. What stops it?</summary>

Nothing in the script: fewer rows would still exit 0. Reading the diff stops it, and so does writing down beforehand which files must not change. Module 8 makes that an approved record, before any code is written.
</details>

<details>
<summary>7. When would the connected path be worth its risk?</summary>

When the handoffs are routine, the limits are real and the work is reversible: a throwaway worktree, an agent with few permissions, a verifier the agent cannot edit, and a person still approving. It saves typing, not judgment. It is not worth it where a wrong move costs more than the time saved.
</details>

<details>
<summary>8. The report says 6 checked. Does that mean the detector works on rice fields?</summary>

No. It means the tests can catch six kinds of break in `infer.py`. Whether the model counts insects well on new photos is a separate question, answered only in part by the evaluation record, and no model here has been validated in the field.
</details>

## References

DeMillo, R. A., Lipton, R. J., & Sayward, F. G. (1978). Hints on test data selection: Help for the practicing programmer. *Computer*, 11(4), 34–41. https://doi.org/10.1109/C-M.1978.218136

Jia, Y., & Harman, M. (2011). An analysis and survey of the development of mutation testing. *IEEE Transactions on Software Engineering*, 37(5), 649–678. https://doi.org/10.1109/TSE.2010.62

Lavaee, A., & Philipose, M. *Formally verifying agent-written full-stack web apps with PDD Kit*. Microsoft Research Blog. Retrieved November 6, 2026, from https://www.microsoft.com/en-us/research/blog/formally-verifying-agent-written-full-stack-web-apps-with-pdd-kit/
