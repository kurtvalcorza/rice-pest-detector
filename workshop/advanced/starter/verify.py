"""STARTER: a fail-closed test verifier. Fill in the TODOs, test-first.

Point the track's tests at this file and watch them fail, then make them pass one at a time:

    RPD_WORKSHOP_IMPL=starter python -m pytest workshop/advanced/tests        # macOS, Linux
    $env:RPD_WORKSHOP_IMPL="starter"; python -m pytest workshop/advanced/tests  # Windows PowerShell

Usage, once finished (the same as the reference in ``workshop/advanced/solutions/verify.py``):
    python verify.py [--evidence DIR] [--min-tests N] [--timeout SECONDS] -- COMMAND [ARG ...]

PASS (exit 0) only when the command exited 0 AND a fresh JUnit report shows at least N tests ran
with none failed. FAIL (exit 1) when the report shows a failure or error. Everything else is
UNVERIFIED (exit 2). The decision table is in specs/004-advanced-workshop/contracts/verifier-cli.md.
Standard library only.
"""

import sys
from dataclasses import dataclass, field

PASS, FAIL, UNVERIFIED = "PASS", "FAIL", "UNVERIFIED"
EXIT_CODES = {PASS: 0, FAIL: 1, UNVERIFIED: 2}
PLACEHOLDER = "{junit}"
MAX_FAILED_NAMES = 20


@dataclass
class ReportCounts:
    tests: int
    failures: int
    errors: int
    skipped: int
    failed_tests: list = field(default_factory=list)


def read_report(path):
    """Return ReportCounts summed over every <testsuite> in the JUnit XML file at ``path``.

    ``failed_tests`` lists ``classname::name`` for each <testcase> with a <failure> or <error>,
    at most MAX_FAILED_NAMES. Return None when the file is missing, is not valid XML, its root is
    not <testsuites> or <testsuite>, or a count is not a number.
    """
    # TODO: parse with xml.etree.ElementTree; catch OSError and ParseError.
    raise NotImplementedError("read_report: TODO")


def classify(command_exit_code, report, min_tests, timed_out, started):
    """Return (result, exit_code, reason) using rows 2-9 of the decision table, first match wins.

    2 not started -> UNVERIFIED; 3 timed out -> UNVERIFIED; 4 no report -> UNVERIFIED;
    5 any failure or error -> FAIL, reason "<n> of <tests> tests failed: <names>";
    6 command exit not 0 -> UNVERIFIED; 7 zero tests or all skipped -> UNVERIFIED;
    8 fewer than min_tests ran (skipped tests do not count) -> UNVERIFIED;
    9 otherwise PASS, reason "<n> tests ran, 0 failed". No input or output.
    """
    # TODO: one `if` per row, in order. Ask yourself: why must the default answer be UNVERIFIED?
    raise NotImplementedError("classify: TODO")


def run(command, evidence, min_tests=1, timeout=600):
    """Run ``command`` (a list, no shell) and return (VerifierResult-like record, output bytes).

    Row 1 first: no command, no {junit} placeholder, min_tests < 1 or timeout <= 0 -> UNVERIFIED.
    Then delete any old junit.xml in ``evidence``, replace {junit} with its path, run the command
    with its output going to a temporary file, stop it after ``timeout`` seconds, read the report
    and classify. A command that is not found gives the reason "command not found: <name>".
    """
    # TODO: shutil.which, subprocess.run(..., timeout=...), read_report, classify.
    raise NotImplementedError("run: TODO")


def main(argv=None):
    """Parse the arguments, call run, write verification.json and run.log, print the output and
    then one last line ``RESULT: <PASS|FAIL|UNVERIFIED> (<reason>) evidence=<folder>``; return the
    exit code. Any unexpected error must end as UNVERIFIED, exit 2, never as PASS.
    """
    # TODO: argparse for --evidence, --min-tests, --timeout; everything after "--" is the command.
    raise NotImplementedError("main: TODO")


if __name__ == "__main__":
    sys.exit(main())
