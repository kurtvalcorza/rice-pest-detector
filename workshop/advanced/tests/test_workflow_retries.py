"""The bounded loop: at most three verification attempts, and only an exit code spends one."""

import json
import sys

import pytest

SEQUENCE_VERIFIER = """
import json, pathlib, sys
queue = pathlib.Path(sys.argv[1])
codes = json.loads(queue.read_text())
queue.write_text(json.dumps(codes[1:]))
sys.exit(codes[0])
"""


def test_three_failures_block_the_task_as_retry_exhausted(reach, send):
    record = send(reach("verifying"), "verifier_fail", "repair_done", "verifier_fail", "repair_done", "verifier_fail")
    assert (record["state"], record["blocked_reason"], record["attempts"]) == ("blocked", "retry_exhausted", 3)
    assert [e["attempt"] for e in record["history"] if e["event"].startswith("verifier_")] == [1, 2, 3]


def test_a_failure_then_a_pass_waits_for_approval_with_two_attempts_used(reach, send):
    record = send(reach("verifying"), "verifier_fail", "repair_done", "verifier_pass")
    assert (record["state"], record["attempts"], record["blocked_reason"]) == ("awaiting_approval", 2, None)


def test_a_pass_on_the_last_attempt_still_counts(reach, send):
    record = send(reach("verifying"), "verifier_fail", "repair_done", "verifier_fail", "repair_done", "verifier_pass")
    assert (record["state"], record["attempts"]) == ("awaiting_approval", 3)


def test_unverified_on_the_first_attempt_blocks_as_verification_unavailable(reach, send):
    record = send(reach("verifying"), "verifier_unverified")
    assert (record["state"], record["blocked_reason"], record["attempts"]) == ("blocked", "verification_unavailable", 1)


def test_unverified_is_never_retried_even_with_attempts_left(reach, send, workflow_mod):
    record = send(reach("verifying"), "verifier_unverified")
    with pytest.raises(workflow_mod.InvalidTransition):
        send(record, "repair_done")


def test_max_attempts_one_blocks_on_the_first_failure(reach, send):
    record = send(reach("verifying", max_attempts=1), "verifier_fail")
    assert (record["state"], record["blocked_reason"], record["attempts"]) == ("blocked", "retry_exhausted", 1)


def test_max_attempts_two_blocks_on_the_second_failure(reach, send):
    record = send(reach("verifying", max_attempts=2), "verifier_fail", "repair_done", "verifier_fail")
    assert (record["state"], record["blocked_reason"]) == ("blocked", "retry_exhausted")


@pytest.mark.parametrize("value", ["0", "4", "-1", "many"])
def test_max_attempts_out_of_range_is_a_usage_error(value, cli):
    done = cli("start", "t1", "--max-attempts", value, "--", "verify")
    assert done.returncode == 2
    assert not (cli.state_dir / "t1.json").exists()


@pytest.mark.parametrize("value", ["1", "2", "3"])
def test_max_attempts_in_range_is_stored(value, cli):
    assert cli("start", "t1", "--max-attempts", value, "--", "verify").returncode == 0
    assert json.loads((cli.state_dir / "t1.json").read_text(encoding="utf-8"))["max_attempts"] == int(value)


def test_max_attempts_defaults_to_three(cli):
    assert cli("start", "t1", "--", "verify").returncode == 0
    assert json.loads((cli.state_dir / "t1.json").read_text(encoding="utf-8"))["max_attempts"] == 3


def test_the_loop_ends_blocked_through_the_command_line(cli, tmp_path):
    script, queue = tmp_path / "sequence.py", tmp_path / "queue.json"
    script.write_text(SEQUENCE_VERIFIER, encoding="utf-8")
    queue.write_text("[1, 1, 1]", encoding="utf-8")
    assert cli("start", "t1", "--", sys.executable, str(script), str(queue)).returncode == 0
    assert cli("event", "t1", "plan_accepted").returncode == 0
    assert cli("event", "t1", "implementation_done", "--actor", "agent").returncode == 0
    for last in (False, False, True):
        assert cli("verify", "t1").returncode == 0  # the event was applied, whatever the new state
        if not last:
            assert cli("event", "t1", "repair_done", "--actor", "agent").returncode == 0
    record = json.loads((cli.state_dir / "t1.json").read_text(encoding="utf-8"))
    assert (record["state"], record["blocked_reason"], record["attempts"]) == ("blocked", "retry_exhausted", 3)
    assert cli("verify", "t1").returncode == 3
    assert json.loads(queue.read_text(encoding="utf-8")) == []
