# Advanced workshop track: runnable material

The pages that teach this material are in [docs/workshop-advanced/](../../docs/workshop-advanced/); start with [Module 6](../../docs/workshop-advanced/module-6-engineer.md). The design is in [specs/004-advanced-workshop/](../../specs/004-advanced-workshop/).

| Folder | What it holds |
| :-- | :-- |
| `solutions/` | The reference scripts (`verify.py`, the fail-closed verifier). CI tests these |
| `starter/` | The same scripts with the same command line and functions, bodies left as `TODO` for learners to fill in, test-first |
| `patches/` | Intentional bugs, as `.patch` files only. A learner applies one with `git apply` in a disposable Git worktree. **Patches are never imported or run in CI, and no Python file may sit in this folder**; a test fails if one does |
| `tests/` | The specification for both `solutions/` and `starter/`, plus safety checks: the patch folder holds no Python, each patch changes only `src/rice_pest_detector/infer.py` and still applies to a copy of it, and the scripts use only the standard library |

## Run the tests

CI runs them with the rest of the suite (`python -m pytest -q` from the repository root). On the light path, without the full install:

```bash
uv run --no-project --python 3.12 --with pytest python -m pytest workshop/advanced/tests
```

## Point the tests at the starter

The tests load the scripts by file path: from `solutions/` by default, from `starter/` when `RPD_WORKSHOP_IMPL` is `starter`. CI never sets it.

```bash
RPD_WORKSHOP_IMPL=starter uv run --no-project --python 3.12 --with pytest python -m pytest workshop/advanced/tests        # macOS, Linux
$env:RPD_WORKSHOP_IMPL="starter"; uv run --no-project --python 3.12 --with pytest python -m pytest workshop/advanced/tests # Windows PowerShell
```

They fail with `NotImplementedError` until the starter is filled in. Clear the variable afterwards (`unset RPD_WORKSHOP_IMPL`, or `Remove-Item Env:RPD_WORKSHOP_IMPL`).
