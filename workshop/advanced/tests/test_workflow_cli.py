"""workflow.py end to end: start, event, verify and show, with exit codes 0, 2, 3 and 4."""

import json
import subprocess
import sys

import pytest


def _exits(code):
    return (sys.executable, "-c", f"import sys; sys.exit({code})")


def _prints(text, code):
    return (sys.executable, "-c", f"import sys; print({text!r}); sys.exit({code})")


def _record(cli, task="t1"):
    return json.loads((cli.state_dir / f"{task}.json").read_text(encoding="utf-8"))


def _at_verifying(cli, *command):
    assert cli("start", "t1", "--", *command).returncode == 0
    assert cli("event", "t1", "plan_accepted").returncode == 0
    assert cli("event", "t1", "implementation_done", "--actor", "agent").returncode == 0


def test_start_writes_a_planning_record(cli):
    done = cli("start", "t1", "--", "python", "verify.py", "--min-tests", "4", "--", "x", "--junitxml={junit}")
    assert done.returncode == 0 and "planning" in done.stdout
    record = _record(cli)
    assert record["state"] == "planning" and record["history"] == []
    assert record["verify_command"] == ["python", "verify.py", "--min-tests", "4", "--", "x", "--junitxml={junit}"]


def test_start_refuses_an_existing_record_and_keeps_it(cli):
    assert cli("start", "t1", "--", "one").returncode == 0
    before = (cli.state_dir / "t1.json").read_bytes()
    assert cli("start", "t1", "--", "two").returncode == 4
    assert (cli.state_dir / "t1.json").read_bytes() == before


def test_start_without_a_command_is_a_usage_error(cli):
    assert cli("start", "t1").returncode == 2
    assert cli("start", "t1", "--").returncode == 2


def test_the_state_folder_is_required(workflow_path, tmp_path):
    done = subprocess.run([sys.executable, str(workflow_path), "show", "t1"], cwd=tmp_path, capture_output=True,
                          check=False)
    assert done.returncode == 2


@pytest.mark.parametrize("args", [("launch", "t1"), ("event", "t1", "ship_it"), ("event", "t1", "approve", "--force"),
                                  ("event", "t1"), ("show",), ("show", "t1", "--", "x")])
def test_an_unknown_command_event_or_option_is_a_usage_error(args, cli):
    assert cli("start", "t1", "--", "verify").returncode == 0
    before = (cli.state_dir / "t1.json").read_bytes()
    assert cli(*args).returncode == 2
    assert (cli.state_dir / "t1.json").read_bytes() == before


def test_a_note_over_500_characters_is_a_usage_error(cli):
    assert cli("start", "t1", "--", "verify").returncode == 0
    assert cli("event", "t1", "plan_accepted", "--note", "x" * 501).returncode == 2
    assert _record(cli)["state"] == "planning"


def test_event_applies_and_records_the_actor_and_note(cli):
    assert cli("start", "t1", "--", "verify").returncode == 0
    done = cli("event", "t1", "plan_accepted", "--note", "plan read")
    assert done.returncode == 0 and "implementing" in done.stdout
    entry = _record(cli)["history"][0]
    assert (entry["actor"], entry["note"], entry["to"]) == ("human", "plan read", "implementing")


def test_a_rejected_event_exits_3_with_a_message_and_changes_no_byte(cli):
    assert cli("start", "t1", "--", "verify").returncode == 0
    before = (cli.state_dir / "t1.json").read_bytes()
    done = cli("event", "t1", "approve")
    assert done.returncode == 3 and "approve" in done.stderr and "planning" in done.stderr
    assert (cli.state_dir / "t1.json").read_bytes() == before


@pytest.mark.parametrize(("code", "state", "reason", "result"), [
    (0, "awaiting_approval", None, "PASS"),
    (1, "repairing", None, "FAIL"),
    (2, "blocked", "verification_unavailable", "UNVERIFIED"),
    (7, "blocked", "verification_unavailable", "UNVERIFIED"),
])
def test_verify_maps_the_exit_code_to_the_next_state(code, state, reason, result, cli):
    _at_verifying(cli, *_exits(code))
    done = cli("verify", "t1")
    assert done.returncode == 0 and state in done.stdout
    record = _record(cli)
    assert (record["state"], record["blocked_reason"], record["attempts"]) == (state, reason, 1)
    assert record["last_verification"]["exit_code"] == code and record["last_verification"]["result"] == result
    assert record["history"][-1]["actor"] == "verifier"


def test_a_command_that_cannot_start_blocks_as_unavailable(cli):
    _at_verifying(cli, "no-such-command-rpd-workshop")
    assert cli("verify", "t1").returncode == 0
    record = _record(cli)
    assert (record["state"], record["blocked_reason"]) == ("blocked", "verification_unavailable")
    assert record["last_verification"]["exit_code"] is None
    assert record["last_verification"]["result"] == "UNVERIFIED"
    assert "no-such-command-rpd-workshop" in record["last_verification"]["reason"]


def test_verify_keeps_the_verifiers_reason(cli):
    _at_verifying(cli, *_prints("RESULT: FAIL (1 of 4 tests failed: a::b) evidence=ev", 1))
    done = cli("verify", "t1")
    assert done.returncode == 0 and "RESULT: FAIL" in done.stdout
    assert _record(cli)["last_verification"]["reason"] == "1 of 4 tests failed: a::b"


def test_the_exit_code_decides_not_the_text(cli):
    _at_verifying(cli, *_prints("RESULT: PASS (everything is fine) evidence=ev", 1))
    assert cli("verify", "t1").returncode == 0
    verification = _record(cli)["last_verification"]
    assert verification["result"] == "FAIL" and "fine" not in verification["reason"]


def test_a_command_with_no_result_line_gets_a_plain_reason(cli):
    _at_verifying(cli, *_exits(1))
    assert cli("verify", "t1").returncode == 0
    assert "exited 1" in _record(cli)["last_verification"]["reason"]


def test_verify_records_the_evidence_folder_the_command_named(cli):
    _at_verifying(cli, sys.executable, "-c", "import sys; sys.exit(0)", "--evidence", "ev/run", "--", "x")
    assert cli("verify", "t1").returncode == 0
    assert _record(cli)["last_verification"]["evidence"] == "ev/run"


def test_verify_leaves_the_evidence_empty_when_none_was_named(cli):
    _at_verifying(cli, *_exits(0))
    assert cli("verify", "t1").returncode == 0
    assert _record(cli)["last_verification"]["evidence"] is None


@pytest.mark.parametrize("route", [(), ("plan_accepted",)])
def test_verify_outside_verifying_is_refused_without_running_the_command(route, cli, tmp_path):
    marker = tmp_path / "ran.txt"
    code = f"open({str(marker)!r}, 'w').close()"
    assert cli("start", "t1", "--", sys.executable, "-c", code).returncode == 0
    for event in route:
        assert cli("event", "t1", event).returncode == 0
    before = (cli.state_dir / "t1.json").read_bytes()
    done = cli("verify", "t1")
    assert done.returncode == 3 and done.stderr.strip()
    assert not marker.exists()
    assert (cli.state_dir / "t1.json").read_bytes() == before


def test_verify_runs_the_command_without_a_shell(cli, tmp_path):
    marker = tmp_path / "shell ran.txt"
    code = "import sys; open(sys.argv[1], 'w').write(sys.argv[2])"
    _at_verifying(cli, sys.executable, "-c", code, str(marker), "a b && exit 9")
    assert cli("verify", "t1").returncode == 0
    assert marker.read_text(encoding="utf-8") == "a b && exit 9"


def test_show_prints_the_record_and_changes_nothing(cli):
    _at_verifying(cli, *_prints("RESULT: FAIL (1 of 4 tests failed: a::b) evidence=ev", 1))
    assert cli("verify", "t1").returncode == 0
    before = (cli.state_dir / "t1.json").read_bytes()
    done = cli("show", "t1")
    assert done.returncode == 0
    assert "repairing" in done.stdout and "1 of 3" in done.stdout and "1 of 4 tests failed: a::b" in done.stdout
    for word in ("seq", "actor", "plan_accepted", "implementation_done", "verifier_fail", "verifier", "agent"):
        assert word in done.stdout
    assert (cli.state_dir / "t1.json").read_bytes() == before


def test_the_contracts_success_walk_runs_on_the_command_line(cli, tmp_path):
    flag = tmp_path / "repaired.txt"
    code = f"import os, sys; sys.exit(0 if os.path.exists({str(flag)!r}) else 1)"
    _at_verifying(cli, sys.executable, "-c", code)
    assert cli("verify", "t1").returncode == 0
    flag.write_text("yes", encoding="utf-8")
    assert cli("event", "t1", "repair_done", "--actor", "agent").returncode == 0
    assert cli("verify", "t1").returncode == 0
    assert cli("event", "t1", "approve", "--note", "diff read").returncode == 0
    record = _record(cli)
    assert (record["state"], record["attempts"]) == ("approved", 2)
    assert [e["seq"] for e in record["history"]] == [1, 2, 3, 4, 5, 6]
    assert not (cli.state_dir / "t1.json.tmp").exists()
