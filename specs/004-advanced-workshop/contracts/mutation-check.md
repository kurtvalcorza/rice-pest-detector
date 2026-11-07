# Contract: mutation check (`mutation_check.py`)

The reference is `workshop/advanced/solutions/mutation_check.py`; the starter in `workshop/advanced/starter/` has the same command line and `NotImplementedError` bodies. Standard library only, Python 3.12. Background and alternatives: [research R10](../research.md#r10-what-the-track-takes-from-proof-driven-development).

The verifier answers "did the tests pass?". This tool answers the next question: "could they have failed?". It plants one known bug per requirement and checks that the verifier rejects each one. A requirement is `checked` only if its bug was caught.

## Mutants file (`workshop/advanced/mutants.json`)

One entry per requirement of the inference contract, each pointing at one patch in `workshop/advanced/patches/`:

| Requirement | Patch | Planted bug | Module 6's four tests | With `tests/test_infer_contract.py` |
| :-- | :-- | :-- | :-- | :-- |
| `orientation` | `m7-orientation.patch` | EXIF orientation is not applied | `unguarded` | `checked` |
| `no-normalisation` | `m6-normalisation.patch` | mean/std normalisation added | `checked` | `checked` |
| `resize-filter` | `m7-resize-filter.patch` | `NEAREST` instead of `BILINEAR` | `unguarded` | `checked` |
| `inclusive-threshold` | `m7-threshold.patch` | `>` instead of `>=` | `checked` | `checked` |
| `sorted-by-score` | `m7-order.patch` | the sort is removed | `unguarded` | `checked` |
| `default-threshold` | `m7-default-threshold.patch` | the default becomes 0.4 | `unguarded` | `checked` |

The file also has an `assumed` list: what no test here reaches, so a person accepts it rather than a check. It holds at least Pillow's and NumPy's own correctness, the trained weights, ONNX Runtime and the app's Dart port. Each entry gives a reason.

The first column was measured on 2026-11-06 at `63ec0bd`, with planted bugs applied to a copy of `infer.py`. Those four bugs also passed every test in the files that touch this code (`test_infer`, `test_export_app_fixtures`, `test_export_onnx`, `test_calibrate_scores`), while a control bug (`>` for `>=`) failed 2. They were real gaps on the Python side, closed by `tests/test_infer_contract.py` the same day. The Dart side has its own tests, which this measurement did not cover.

## Command

```text
python workshop/advanced/solutions/mutation_check.py --mutants workshop/advanced/mutants.json --evidence DIR -- VERIFY_COMMAND [ARG ...]
```

`VERIFY_COMMAND` is the same `verify.py` call Module 6 built. The steps are:

1. Refuse to run unless the current directory is a linked Git worktree with a clean tree (exit 2). Bugs are never applied in the learner's main clone.
2. Run the verify command on the unchanged code. Anything but exit 0 stops the run (exit 2): a check that fails before any bug is planted proves nothing.
3. For each mutant: apply the patch, run the verify command, reverse the patch, and confirm the tree is clean again. A patch that cannot be applied or reversed stops the run (exit 2). Every run clears `__pycache__` under `src` and sets `PYTHONDONTWRITEBYTECODE=1`: Python trusts cached bytecode when the source's size and whole-second time match, and a same-size bug can come and go within one second.
4. Write `mutation-report.json` to `DIR`, print one line per requirement and a `RESULT:` line.

## Verdict per requirement

| Verify command exit | Mutant | Label | Meaning |
| :-- | :-- | :-- | :-- |
| 1 | killed | `checked` | A test failed when this requirement was broken |
| 0 | survived | `unguarded` | The requirement was broken and every test still passed |
| anything else | not judged | `unverified` | The check could not run; nothing is known |

`assumed` items are copied from the mutants file and never tested.

## Exit codes

| Code | Meaning |
| :-- | :-- |
| 0 | Every requirement is `checked` |
| 1 | At least one is `unguarded`, none `unverified` |
| 2 | Could not judge: usage error, not a clean linked worktree, baseline not passing, a patch problem, or any `unverified` row |

## Report (`mutation-report.json`)

`schema`, `commit`, `baseline` (the verifier's result), `requirements` (each with `id`, `patch`, `label`, `verifier_exit`, `reason`), `assumed` (each with `item`, `reason`), and `counts` (`checked`, `unguarded`, `unverified`).

## What this does not show

Stated on Module 7's page. `checked` means one planted bug was caught, not that the requirement holds for every input: this is testing, not proof. A requirement that nobody wrote down has no mutant, so the tool cannot notice it. A person still decides whether the requirement list is right.
