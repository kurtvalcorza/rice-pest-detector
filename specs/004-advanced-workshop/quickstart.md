# Quickstart: Advanced Workshop Track

How a maintainer checks the track once the tasks are done. Needs Git, `uv` and Python 3.12 (or let `uv` fetch it); Module 8 also needs the GitHub CLI and a GitHub account. No PyTorch, Flutter, emulator or model weights.

## Run the track's tests

As CI does (full install, from the repository root; see `docs/setup.md`, "Python tools and tests"):

```bash
python -m pytest -q
```

On the light path, only the track and the inference tests:

```bash
uv run --no-project --python 3.12 --with numpy==2.5.4 --with pillow==13.0.0 --with pytest --with-editable . python -m pytest tests/test_infer.py workshop/advanced/tests workshop/advanced/solutions
```

Point the same tests at the starter files; they fail with `NotImplementedError` until a learner fills them in:

```bash
RPD_WORKSHOP_IMPL=starter uv run --no-project --python 3.12 --with pytest python -m pytest workshop/advanced/tests      # macOS, Linux
$env:RPD_WORKSHOP_IMPL="starter"; uv run --no-project --python 3.12 --with pytest python -m pytest workshop/advanced/tests # Windows PowerShell
```

## Walk Module 6 (about 10 minutes for a maintainer)

```bash
mkdir -p ../agents-practice/advanced-evidence/m6
git worktree add ../rpd-m6 -b m6-practice
cd ../rpd-m6
LIGHT="uv run --no-project --python 3.12 --with numpy==2.5.4 --with pillow==13.0.0 --with pytest --with-editable . python -m pytest tests/test_infer.py --junitxml={junit}"
python workshop/advanced/solutions/verify.py --evidence ../agents-practice/advanced-evidence/m6/baseline --min-tests 4 -- $LIGHT     # RESULT: PASS, exit 0
git apply workshop/advanced/patches/m6-normalisation.patch
git diff > ../agents-practice/advanced-evidence/m6/regression.diff
python workshop/advanced/solutions/verify.py --evidence ../agents-practice/advanced-evidence/m6/regression --min-tests 4 -- $LIGHT   # RESULT: FAIL, exit 1
python .claude/hooks/require_green_tests.py                                                                                          # allows the stop either way
python workshop/advanced/solutions/verify.py --evidence ../agents-practice/advanced-evidence/m6/unavailable -- no-such-runner {junit} # RESULT: UNVERIFIED, exit 2
git restore src/rice_pest_detector/infer.py
python workshop/advanced/solutions/verify.py --evidence ../agents-practice/advanced-evidence/m6/restored --min-tests 4 -- $LIGHT     # RESULT: PASS, exit 0
cd ../rice-pest-detector
git worktree remove --force ../rpd-m6
git branch -D m6-practice
```

(The `LIGHT` variable is a bash shortcut for this page; the module page writes the command out for PowerShell and bash.)

## Walk Module 7

In a fresh `../rpd-m7` worktree with the patch applied:

```bash
W="python workshop/advanced/solutions/workflow.py --state-dir ../agents-practice/advanced-evidence/m7/records"
$W start m7-success -- python workshop/advanced/solutions/verify.py --min-tests 4 -- <the light command with --junitxml={junit}>
$W event m7-success plan_accepted
$W event m7-success implementation_done --actor agent
$W verify m7-success              # FAIL -> repairing (patch still applied)
git restore src/rice_pest_detector/infer.py
$W event m7-success repair_done --actor agent
$W verify m7-success              # PASS -> awaiting_approval
$W event m7-success approve --note "diff read"
$W show m7-success                # approved, attempts 2
$W event m7-success approve; echo $?   # 3: not allowed in approved
```

Repeat with a task `m7-exhaustion`, leaving the patch in place for three `verify` runs: it ends `blocked`, `retry_exhausted`, attempts 3. Compare both records with `workshop/advanced/solutions/traces/`.

## Walk Module 8

Follow `docs/workshop-advanced/module-8-automate.md` in a throwaway fork. Done when: the pull request is in the fork, the fork's Tests workflow ran on it, `gh pr list --repo kurtvalcorza/rice-pest-detector --author @me` shows nothing new, and the fork is deleted afterwards if it was only for this check.

## Check nothing else changed

```bash
git diff --stat main -- src app docs/inference-contract.md .claude .github pyproject.toml requirements.txt   # empty (SC-007)
git diff main -- docs/workshop-setup.md                                                                      # one paragraph and one table row added (SC-009)
```
