"""verify.py end to end: exit codes, the RESULT line and the evidence files, on tiny throwaway projects."""

import json
import subprocess
import sys
import textwrap
import time

import pytest

FAKE_RUNNER = textwrap.dedent("""
    import sys
    junit, failures, exit_code = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
    cases = "".join('<testcase classname="fake" name="t%d">%s</testcase>' % (i, "<failure/>" if i < failures else "")
                    for i in range(4))
    with open(junit, "w", encoding="utf-8") as f:
        f.write('<testsuite tests="4" failures="%d" errors="0" skipped="0">%s</testsuite>' % (failures, cases))
    print("fake runner wrote", failures, "failures")
    sys.exit(exit_code)
""")


@pytest.fixture
def project(tmp_path):
    """Write a tiny pytest project and return a function giving the command that tests it."""
    def make(body, folder="proj"):
        root = tmp_path / folder
        root.mkdir()
        (root / "pytest.ini").write_text("[pytest]\n", encoding="utf-8")
        (root / "test_tiny.py").write_text(textwrap.dedent(body), encoding="utf-8")
        return [sys.executable, "-m", "pytest", "-p", "no:cacheprovider", "-q", str(root), "--junitxml={junit}"]
    return make


@pytest.fixture
def verify(verify_path, tmp_path):
    def run(command, *options, evidence="evidence", timeout=120):
        args = [sys.executable, str(verify_path)]
        if evidence is not None:
            args += ["--evidence", str(tmp_path / evidence)]
        done = subprocess.run(args + list(options) + ["--"] + list(command), cwd=tmp_path, capture_output=True,
                              text=True, encoding="utf-8", errors="replace", timeout=timeout, check=False)
        lines = done.stdout.strip().splitlines()
        return done.returncode, (lines[-1] if lines else ""), done
    return run


def _evidence(tmp_path, folder="evidence"):
    return json.loads((tmp_path / folder / "verification.json").read_text(encoding="utf-8"))


def test_one_passing_test_is_pass_with_its_evidence(project, verify, tmp_path):
    code, line, _ = verify(project("def test_ok():\n    assert True\n"))
    assert code == 0 and line.startswith("RESULT: PASS (1 tests ran, 0 failed)")
    assert line.endswith("evidence=" + str(tmp_path / "evidence"))
    record = _evidence(tmp_path)
    assert record["result"] == "PASS" and record["exit_code"] == 0 and record["command_exit_code"] == 0
    assert record["report"]["tests"] == 1 and record["min_tests"] == 1
    assert record["log"] == "run.log" and record["junit"] == "junit.xml"
    assert "{junit}" not in " ".join(record["command"])
    assert str(tmp_path / "evidence" / "junit.xml") in record["command"][-1]
    assert record["started_at"].endswith("Z") and record["duration_seconds"] >= 0
    assert (tmp_path / "evidence" / "junit.xml").is_file()
    assert "1 passed" in (tmp_path / "evidence" / "run.log").read_text(encoding="utf-8")


def test_a_failing_test_is_fail_and_names_the_test(project, verify, tmp_path):
    code, line, _ = verify(project("def test_ok():\n    pass\n\ndef test_broken():\n    assert 1 == 2\n"))
    assert code == 1 and line.startswith("RESULT: FAIL (1 of 2 tests failed:") and "test_broken" in line
    assert _evidence(tmp_path)["report"]["failed_tests"] == ["test_tiny::test_broken"]


def test_no_tests_is_unverified(project, verify, tmp_path):
    code, line, _ = verify(project("# nothing here yet\n"))
    assert code == 2 and line.startswith("RESULT: UNVERIFIED")
    assert _evidence(tmp_path)["result"] == "UNVERIFIED"


def test_every_test_skipped_is_unverified(project, verify, tmp_path):
    code, line, _ = verify(project("import pytest\n\n@pytest.mark.skip\ndef test_later():\n    pass\n"))
    assert code == 2 and "skip" in line.lower()


def test_fewer_tests_than_required_is_unverified(project, verify, tmp_path):
    code, line, _ = verify(project("def test_ok():\n    pass\n"), "--min-tests", "4")
    assert code == 2 and line.startswith("RESULT: UNVERIFIED") and "4" in line


def test_a_command_that_does_not_exist_is_unverified(verify, tmp_path):
    code, line, _ = verify(["no-such-runner-for-the-workshop", "{junit}"])
    assert code == 2 and "command not found: no-such-runner-for-the-workshop" in line
    record = _evidence(tmp_path)
    assert record["command_exit_code"] is None and record["report"] is None
    assert (tmp_path / "evidence" / "run.log").is_file()


def test_a_command_that_runs_too_long_is_stopped_and_unverified(verify, tmp_path):
    began = time.monotonic()
    code, line, _ = verify([sys.executable, "-c", "import time; time.sleep(60)", "{junit}"], "--timeout", "2")
    assert code == 2 and "timed out" in line
    assert time.monotonic() - began < 30
    assert _evidence(tmp_path)["command_exit_code"] is None


def test_a_command_without_the_junit_placeholder_is_unverified(project, verify, tmp_path):
    command = [c for c in project("def test_ok():\n    pass\n") if "{junit}" not in c]
    code, line, _ = verify(command)
    assert code == 2 and "{junit}" in line
    assert _evidence(tmp_path)["result"] == "UNVERIFIED"


@pytest.mark.parametrize("options", [["--min-tests", "0"], ["--timeout", "0"]])
def test_invalid_limits_are_unverified(project, verify, options):
    code, line, _ = verify(project("def test_ok():\n    pass\n"), *options)
    assert code == 2 and line.startswith("RESULT: UNVERIFIED")


def test_no_command_at_all_is_unverified(verify):
    code, line, _ = verify([])
    assert code == 2 and line.startswith("RESULT: UNVERIFIED")


def test_a_stale_report_is_deleted_and_never_reused(verify, tmp_path):
    evidence = tmp_path / "evidence"
    evidence.mkdir()
    (evidence / "junit.xml").write_text(
        '<testsuite tests="9" failures="0" errors="0" skipped="0"/>', encoding="utf-8")
    code, line, _ = verify([sys.executable, "-c", "import sys", "{junit}"])
    assert code == 2 and line.startswith("RESULT: UNVERIFIED")
    assert not (evidence / "junit.xml").exists()
    assert _evidence(tmp_path)["report"] is None


def test_a_passing_report_from_a_failing_command_is_unverified(verify, tmp_path):
    (tmp_path / "fake_runner.py").write_text(FAKE_RUNNER, encoding="utf-8")
    code, line, _ = verify([sys.executable, str(tmp_path / "fake_runner.py"), "{junit}", "0", "3"])
    assert code == 2 and line.startswith("RESULT: UNVERIFIED")


def test_a_failing_report_from_a_command_that_exited_0_is_fail(verify, tmp_path):
    (tmp_path / "fake_runner.py").write_text(FAKE_RUNNER, encoding="utf-8")
    code, line, _ = verify([sys.executable, str(tmp_path / "fake_runner.py"), "{junit}", "1", "0"])
    assert code == 1 and line.startswith("RESULT: FAIL (1 of 4 tests failed:")


def test_paths_with_spaces_work(project, verify, tmp_path):
    command = project("def test_ok():\n    pass\n", folder="my project")
    code, line, _ = verify(command, evidence="my evidence")
    assert code == 0 and line.startswith("RESULT: PASS")
    assert _evidence(tmp_path, "my evidence")["result"] == "PASS"


def test_without_an_evidence_folder_a_new_one_is_made_and_named(project, verify):
    code, line, _ = verify(project("def test_ok():\n    pass\n"), evidence=None)
    assert code == 0
    from pathlib import Path
    folder = Path(line.split("evidence=", 1)[1])
    assert (folder / "verification.json").is_file()


def test_the_result_line_is_always_the_last_line(project, verify):
    _, _, done = verify(project("def test_ok():\n    pass\n"))
    assert done.stdout.rstrip().splitlines()[-1].startswith("RESULT: ")
    assert "1 passed" in done.stdout  # the run's own output is shown before the result
