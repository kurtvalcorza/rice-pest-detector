"""A fail-closed test verifier: PASS only when the tests really ran and really passed.

Usage:
    python verify.py [--evidence DIR] [--min-tests N] [--timeout SECONDS] -- COMMAND [ARG ...]

The command is run without a shell. Every argument containing ``{junit}`` gets the path of a fresh
JUnit XML report inside the evidence folder. The result is judged on two independent signals, the
command's exit code and that report, using the decision table in
``specs/004-advanced-workshop/contracts/verifier-cli.md``:

    PASS        exit 0  the command exited 0 and the report shows enough tests, none failed
    FAIL        exit 1  the report shows at least one failure or error: the tests ran and said no
    UNVERIFIED  exit 2  anything else: nothing trustworthy happened, so stop and look

The evidence folder gets ``verification.json``, ``run.log`` and (when the command wrote one)
``junit.xml``. Standard library only; works with any agent, or none.
"""

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
import time
import xml.etree.ElementTree as ET
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path

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


@dataclass
class VerifierResult:
    result: str
    exit_code: int
    reason: str
    command: list
    command_exit_code: int | None
    report: dict | None
    min_tests: int
    started_at: str
    finished_at: str
    duration_seconds: float
    log: str = "run.log"
    junit: str = "junit.xml"


class UsageError(Exception):
    """Invalid arguments: decision-table row 1."""


def _now():
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def read_report(path):
    """Counts summed over every <testsuite> in a JUnit XML file; None if missing or not a valid report."""
    try:
        root = ET.parse(path).getroot()
    except (OSError, ET.ParseError):
        return None
    if root.tag == "testsuite":
        suites = [root]
    elif root.tag == "testsuites":
        suites = [s for s in root.iter("testsuite") if s.find("testsuite") is None]  # leaves: no double count
    else:
        return None
    totals = {"tests": 0, "failures": 0, "errors": 0, "skipped": 0}
    failed = []
    try:
        for suite in suites:
            for key in totals:
                totals[key] += int(suite.get(key, "0"))
            for case in suite.iter("testcase"):
                if case.find("failure") is not None or case.find("error") is not None:
                    failed.append(f"{case.get('classname', '')}::{case.get('name', '')}")
    except ValueError:
        return None
    if any(value < 0 for value in totals.values()):
        return None
    return ReportCounts(failed_tests=failed[:MAX_FAILED_NAMES], **totals)


def classify(command_exit_code, report, min_tests, timed_out, started):
    """Rows 2-9 of the decision table, first match wins. Pure: no input or output."""
    if not started:
        return UNVERIFIED, 2, "the command could not start"
    if timed_out:
        return UNVERIFIED, 2, "the command timed out"
    if report is None:
        return UNVERIFIED, 2, "no readable test report was written"
    broken = report.failures + report.errors
    if broken:
        names = ", ".join(report.failed_tests) or "names not in the report"
        return FAIL, 1, f"{broken} of {report.tests} tests failed: {names}"
    if command_exit_code != 0:
        return UNVERIFIED, 2, f"the command exited {command_exit_code} but the report shows no failure"
    ran = report.tests - report.skipped
    if report.tests == 0:
        return UNVERIFIED, 2, "the report shows 0 tests"
    if ran <= 0:
        return UNVERIFIED, 2, f"all {report.tests} tests were skipped"
    if ran < min_tests:
        return UNVERIFIED, 2, f"{ran} tests ran, fewer than the {min_tests} required"
    skipped = f" ({report.skipped} skipped)" if report.skipped else ""
    return PASS, 0, f"{ran} tests ran{skipped}, 0 failed"


def _write_evidence(evidence, result, output):
    evidence.mkdir(parents=True, exist_ok=True)
    text = output.decode("utf-8", errors="replace") if isinstance(output, bytes) else output
    (evidence / "run.log").write_text(text, encoding="utf-8")
    (evidence / "verification.json").write_text(json.dumps(asdict(result), indent=2) + "\n", encoding="utf-8")
    return text


def run(command, evidence, min_tests=1, timeout=600):
    """Run the command, judge it, write the evidence files and return the result (rows 1-9)."""
    evidence = Path(evidence)
    evidence.mkdir(parents=True, exist_ok=True)
    junit = evidence / "junit.xml"
    resolved = [arg.replace(PLACEHOLDER, str(junit)) for arg in command]
    started_at, began = _now(), time.monotonic()
    exit_code, timed_out, started, output, detail = None, False, False, b"", None

    def finish(result, code, reason, report):
        return VerifierResult(result, code, reason, resolved, exit_code, report and asdict(report), min_tests,
                              started_at, _now(), round(time.monotonic() - began, 3))

    problem = None
    if not command:
        problem = "no command was given after --"
    elif not any(PLACEHOLDER in arg for arg in command):
        problem = f"the command has no {PLACEHOLDER} placeholder, so no fresh report can be read"
    elif min_tests < 1:
        problem = "--min-tests must be at least 1"
    elif timeout <= 0:
        problem = "--timeout must be more than 0 seconds"
    if problem:
        return finish(UNVERIFIED, 2, problem, None), b""

    junit.unlink(missing_ok=True)  # never judge a report left over from an earlier run
    program = shutil.which(resolved[0])
    if program is None:
        detail = f"command not found: {resolved[0]}"
    else:
        with tempfile.TemporaryFile() as log:  # a file, not a pipe: a timed-out grandchild cannot hang us
            try:
                done = subprocess.run([program, *resolved[1:]], stdout=log, stderr=subprocess.STDOUT,
                                      stdin=subprocess.DEVNULL, timeout=timeout, check=False)
                started, exit_code = True, done.returncode
            except subprocess.TimeoutExpired:
                started, timed_out = True, True
            except OSError as exc:
                detail = f"the command could not start: {exc.strerror or exc}"
            log.seek(0)
            output = log.read()
    report = None if (timed_out or not started) else read_report(junit)
    result, code, reason = classify(exit_code, report, min_tests, timed_out, started)
    if detail and not started:
        reason = detail
    elif timed_out:
        reason = f"the command timed out after {timeout:g} seconds"
    return finish(result, code, reason, report), output


class _Parser(argparse.ArgumentParser):
    def error(self, message):
        raise UsageError(message)


def _parse(argv):
    if "--" in argv:
        split = argv.index("--")
        options, command = argv[:split], argv[split + 1:]
    else:
        options, command = argv, []
    parser = _Parser(prog="verify.py", description=__doc__.splitlines()[0])
    parser.add_argument("--evidence", type=Path, default=None)
    parser.add_argument("--min-tests", type=int, default=1)
    parser.add_argument("--timeout", type=float, default=600.0)
    return parser.parse_args(options), command


def _result_line(result, evidence):
    return f"RESULT: {result.result} ({result.reason}) evidence={evidence}"


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    evidence = None
    try:
        args, command = _parse(argv)
        evidence = args.evidence or Path(tempfile.mkdtemp(prefix="verify-"))
        result, output = run(command, evidence, args.min_tests, args.timeout)
        text = _write_evidence(evidence, result, output)
        if text:
            print(text.rstrip())
        print(_result_line(result, evidence))
        return result.exit_code
    except UsageError as exc:
        print(f"RESULT: UNVERIFIED (invalid arguments: {exc}) evidence=none")
        return 2
    except Exception as exc:  # noqa: BLE001 - fail closed: a crash in the verifier is never a PASS
        print(f"RESULT: UNVERIFIED (verifier error: {type(exc).__name__}: {exc}) evidence={evidence or 'none'}")
        return 2


if __name__ == "__main__":
    sys.exit(main())
