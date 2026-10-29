# Contract: verifier command line (`verify.py`)

The reference is `workshop/advanced/solutions/verify.py`; the starter in `workshop/advanced/starter/verify.py` has the same command line and functions. Standard library only, Python 3.12. Design and alternatives: [research R2](../research.md#r2-the-verifier-fail-closed-design).

## Usage

```text
python workshop/advanced/solutions/verify.py [--evidence DIR] [--min-tests N] [--timeout SECONDS] -- COMMAND [ARG ...]
```

| Option | Default | Meaning |
| :-- | :-- | :-- |
| `--evidence DIR` | a new temporary folder (path printed) | Where `verification.json`, `run.log` and `junit.xml` go; created if missing |
| `--min-tests N` | 1 | Fewest tests the report must show for PASS; N ≥ 1 |
| `--timeout SECONDS` | 600 | The command is stopped after this long; result UNVERIFIED |
| `COMMAND ...` | required | Run without a shell. Every argument equal to or containing `{junit}` has it replaced by the report path |

Module 6's command (the light path, research R3):

```bash
python workshop/advanced/solutions/verify.py --evidence ../agents-practice/advanced-evidence/m6/regression --min-tests 4 -- uv run --no-project --python 3.12 --with numpy==2.5.4 --with pillow==13.0.0 --with pytest --with-editable . python -m pytest tests/test_infer.py --junitxml={junit}
```

## Decision table

Checked top to bottom; the first row that matches decides.

| # | Situation | Result | Exit |
| :-- | :-- | :-- | :-- |
| 1 | Arguments invalid: no command, no `{junit}` in the command, `--min-tests` < 1, `--timeout` ≤ 0 | UNVERIFIED | 2 |
| 2 | The command cannot start (not found, not executable) | UNVERIFIED | 2 |
| 3 | The command runs past `--timeout` | UNVERIFIED | 2 |
| 4 | No report file after the run, or it is not valid JUnit XML | UNVERIFIED | 2 |
| 5 | The report shows ≥ 1 failure or error | FAIL | 1 |
| 6 | The command exited non-zero (and the report shows no failure) | UNVERIFIED | 2 |
| 7 | The report shows 0 tests, or every test skipped | UNVERIFIED | 2 |
| 8 | The report shows fewer than `--min-tests` tests that ran (skipped tests do not count) | UNVERIFIED | 2 |
| 9 | Command exited 0; report: ≥ `--min-tests` tests, 0 failures, 0 errors, not all skipped | PASS | 0 |

Before row 2, any existing file at the report path is deleted (no stale reports). Any unexpected exception inside the verifier itself is caught at the top level and reported as UNVERIFIED, exit 2, with the exception type in `reason`.

Exit 1 means "the tests ran and said no": worth repairing. Exit 2 means "nothing trustworthy happened": stop and look. Callers MUST treat every code other than 0 as "not verified".

## Output

Standard output, one line, always last:

```text
RESULT: PASS (4 tests ran, 0 failed) evidence=../agents-practice/advanced-evidence/m6/restored
RESULT: FAIL (1 of 4 tests failed: tests.test_infer::test_preprocess_shape_range_and_no_normalisation) evidence=...
RESULT: UNVERIFIED (command not found: uv) evidence=...
```

Files in the evidence folder: `verification.json` ([data-model](../data-model.md#verifier-result-verificationjson)), `run.log` (the command's output, UTF-8, undecodable bytes replaced), `junit.xml` (when the command wrote one).

## Functions (tested directly)

| Function | Returns |
| :-- | :-- |
| `read_report(path) -> ReportCounts or None` | Summed counts over every `<testsuite>`; None for a missing or invalid file |
| `classify(command_exit_code, report, min_tests, timed_out, started) -> (result, exit_code, reason)` | Applies rows 2–9; pure, no I/O |
| `run(command, evidence, min_tests, timeout) -> VerifierResult` | Does rows 1–9 and writes the files |
| `main(argv) -> int` | The exit code |
