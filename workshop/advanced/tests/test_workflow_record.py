"""The record: the data model's invariants, atomic writes, and the two reference traces."""

import copy
import json
import re
from pathlib import Path

import pytest

TRACES = Path(__file__).resolve().parents[1] / "solutions" / "traces"
TIME = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
SUCCESS_ROUTE = ("verifier_fail", "repair_done", "verifier_pass", "approve")


@pytest.fixture
def finished(reach, send):
    return send(reach("verifying"), *SUCCESS_ROUTE)


def test_a_new_record_starts_in_planning_with_an_empty_history(workflow_mod):
    record = workflow_mod.new_record("m7-success", ["python", "verify.py"], 2)
    assert record["schema"] == 1 and record["task_id"] == "m7-success"
    assert (record["state"], record["attempts"], record["max_attempts"]) == ("planning", 0, 2)
    assert record["verify_command"] == ["python", "verify.py"]
    assert record["last_verification"] is None and record["blocked_reason"] is None and record["history"] == []
    assert TIME.match(record["created_at"]) and record["created_at"] == record["updated_at"]


def test_a_record_survives_a_round_trip_through_its_file(finished, workflow_mod, tmp_path):
    workflow_mod.save_record(tmp_path, finished)
    assert workflow_mod.load_record(tmp_path, "t1") == finished


def test_a_verifier_entry_holds_its_attempt_and_result(reach, send):
    record = send(reach("verifying"), "verifier_fail")
    entry = record["history"][-1]
    assert (entry["actor"], entry["attempt"]) == ("verifier", 1)
    assert entry["verification"] == {"exit_code": 1, "result": "FAIL", "reason": "1 of 4 tests failed: t::x"}
    assert record["last_verification"] == {**entry["verification"], "evidence": None}


def test_the_evidence_folder_is_kept_in_the_last_verification_only(reach, workflow_mod):
    verification = {"exit_code": 0, "result": "PASS", "reason": "4 tests ran, 0 failed"}
    record = workflow_mod.apply_event(reach("verifying"), "verifier_pass", "verifier",
                                      verification=verification, evidence="evidence/run")
    assert record["last_verification"]["evidence"] == "evidence/run"
    assert "evidence" not in record["history"][-1]["verification"]


def test_every_time_is_utc_with_a_z(finished):
    times = [finished["created_at"], finished["updated_at"], *(e["at"] for e in finished["history"])]
    assert all(TIME.match(value) for value in times)


def test_a_record_that_really_travelled_is_valid(finished, workflow_mod):
    workflow_mod.validate_record(finished)


def _set(*path_and_value):
    *path, key, value = path_and_value

    def change(record):
        target = record
        for part in path:
            target = target[part]
        target[key] = value
    return change


BROKEN = {
    "schema": _set("schema", 2),
    "task id": _set("task_id", "../x"),
    "unknown state": _set("state", "done"),
    "state differs from the last entry": _set("state", "verifying"),
    "attempts differ from the verifier entries": _set("attempts", 1),
    "attempts above the maximum": _set("attempts", 4),
    "attempts not a number": _set("attempts", "2"),
    "maximum out of range": _set("max_attempts", 4),
    "no verify command": _set("verify_command", []),
    "verify command not strings": _set("verify_command", ["python", 3]),
    "blocked reason while approved": _set("blocked_reason", "retry_exhausted"),
    "no created_at": lambda record: record.pop("created_at"),
    "a bad time": _set("updated_at", "yesterday"),
    "an extra field": _set("extra", True),
    "history not a list": _set("history", {}),
    "last verification lost": _set("last_verification", None),
    "last verification differs": _set("last_verification", "result", "FAIL"),
    "seq gap": _set("history", 2, "seq", 9),
    "seq restarts": _set("history", 1, "seq", 1),
    "an entry removed": lambda record: record["history"].pop(2),
    "a row not in the table": _set("history", 0, "to", "approved"),
    "a broken chain": _set("history", 1, "from", "repairing"),
    "unknown event": _set("history", 0, "event", "force"),
    "unknown actor": _set("history", 0, "actor", "robot"),
    "approve by the agent": _set("history", -1, "actor", "agent"),
    "plan accepted by the agent": _set("history", 0, "actor", "agent"),
    "verifier entry by the agent": _set("history", 2, "actor", "agent"),
    "attempt number wrong": _set("history", 2, "attempt", 2),
    "attempt on a plain entry": _set("history", 0, "attempt", 1),
    "verification on a plain entry": _set("history", 0, "verification", {"exit_code": 0}),
    "verifier entry without its result": _set("history", 2, "verification", None),
    "a result that contradicts the event": _set("history", 2, "verification", "result", "PASS"),
    "note too long": _set("history", 0, "note", "x" * 501),
    "entry missing a field": lambda record: record["history"][0].pop("at"),
}


@pytest.mark.parametrize("name", list(BROKEN))
def test_an_invariant_violation_is_refused(name, finished, workflow_mod):
    record = copy.deepcopy(finished)
    BROKEN[name](record)
    with pytest.raises(workflow_mod.RecordError):
        workflow_mod.validate_record(record)


def test_reject_by_the_agent_breaks_an_invariant(reach, workflow_mod):
    record = reach("blocked")
    record["history"][-1]["actor"] = "agent"
    with pytest.raises(workflow_mod.RecordError):
        workflow_mod.validate_record(record)


@pytest.mark.parametrize("reason", [None, "retry_exhausted"])
def test_a_blocked_record_keeps_the_reason_its_transition_set(reason, reach, workflow_mod):
    record = reach("blocked")
    record["blocked_reason"] = reason
    with pytest.raises(workflow_mod.RecordError):
        workflow_mod.validate_record(record)


def test_an_exhausted_task_cannot_claim_more_room(reach, send, workflow_mod):
    record = send(reach("verifying", max_attempts=2), "verifier_fail", "repair_done", "verifier_fail")
    record["max_attempts"] = 3
    with pytest.raises(workflow_mod.RecordError):
        workflow_mod.validate_record(record)


def test_an_empty_history_must_mean_planning(reach, workflow_mod):
    record = reach("planning")
    record["state"] = "implementing"
    with pytest.raises(workflow_mod.RecordError):
        workflow_mod.validate_record(record)


def test_a_note_of_500_characters_is_allowed(reach, workflow_mod):
    workflow_mod.validate_record(workflow_mod.apply_event(reach("planning"), "plan_accepted", "human", note="x" * 500))


def test_earlier_entries_stay_byte_identical_after_a_new_event(reach, send, workflow_mod, tmp_path):
    record = reach("verifying")
    workflow_mod.save_record(tmp_path, record)
    before = json.loads((tmp_path / "t1.json").read_text(encoding="utf-8"))["history"]
    workflow_mod.save_record(tmp_path, send(record, "verifier_fail"))
    after = json.loads((tmp_path / "t1.json").read_text(encoding="utf-8"))["history"]
    assert len(after) == len(before) + 1
    assert [json.dumps(entry) for entry in after[:-1]] == [json.dumps(entry) for entry in before]


def test_a_failed_write_leaves_the_old_file(reach, send, workflow_mod, tmp_path, monkeypatch):
    record = reach("verifying")
    workflow_mod.save_record(tmp_path, record)
    before = (tmp_path / "t1.json").read_bytes()

    def refuse(*_):
        raise OSError("disk full")
    monkeypatch.setattr(workflow_mod.os, "replace", refuse)
    with pytest.raises(workflow_mod.RecordError):
        workflow_mod.save_record(tmp_path, send(record, "verifier_fail"))
    assert (tmp_path / "t1.json").read_bytes() == before
    assert not (tmp_path / "t1.json.tmp").exists()


def test_a_write_goes_through_the_temporary_name(reach, workflow_mod, tmp_path, monkeypatch):
    calls = []
    real = workflow_mod.os.replace

    def spy(source, target):
        calls.append((Path(source).name, Path(target).name))
        real(source, target)
    monkeypatch.setattr(workflow_mod.os, "replace", spy)
    workflow_mod.save_record(tmp_path, reach("planning"))
    assert calls == [("t1.json.tmp", "t1.json")]


def test_a_missing_file_is_a_record_error(workflow_mod, tmp_path):
    with pytest.raises(workflow_mod.RecordError):
        workflow_mod.load_record(tmp_path, "t1")


@pytest.mark.parametrize("text", ["{not json", "[]", "null", ""])
def test_a_corrupt_file_is_a_record_error(text, workflow_mod, tmp_path):
    (tmp_path / "t1.json").write_text(text, encoding="utf-8")
    with pytest.raises(workflow_mod.RecordError):
        workflow_mod.load_record(tmp_path, "t1")


def test_undecodable_bytes_are_a_record_error(workflow_mod, tmp_path):
    (tmp_path / "t1.json").write_bytes(b"\xff\xfe\x00")
    with pytest.raises(workflow_mod.RecordError):
        workflow_mod.load_record(tmp_path, "t1")


def test_a_record_filed_under_another_name_is_refused(reach, workflow_mod, tmp_path):
    workflow_mod.save_record(tmp_path, reach("planning"))
    (tmp_path / "t1.json").rename(tmp_path / "t2.json")
    with pytest.raises(workflow_mod.RecordError):
        workflow_mod.load_record(tmp_path, "t2")


@pytest.mark.parametrize("command", [("event", "t1", "plan_accepted"), ("verify", "t1"), ("show", "t1")])
@pytest.mark.parametrize("problem", ["corrupt", "missing", "invariant"])
def test_a_bad_record_stops_every_command_with_exit_4(problem, command, cli):
    assert cli("start", "t1", "--", "verify").returncode == 0
    path = cli.state_dir / "t1.json"
    if problem == "missing":
        path.unlink()
    elif problem == "corrupt":
        path.write_text("{not json", encoding="utf-8")
    else:
        record = json.loads(path.read_text(encoding="utf-8"))
        path.write_text(json.dumps({**record, "state": "approved"}), encoding="utf-8")
    before = path.read_bytes() if path.exists() else None
    done = cli(*command)
    assert done.returncode == 4 and done.stderr.strip()
    assert (path.read_bytes() if path.exists() else None) == before


@pytest.mark.parametrize("task", ["../x", "A", "a/b", "a\\b", "-a", "", "a" * 41, "a.b", "a\n"])
def test_a_bad_task_id_is_refused(task, cli):
    assert cli("start", task, "--", "verify").returncode == 2
    assert not cli.state_dir.exists() or list(cli.state_dir.iterdir()) == []


@pytest.mark.parametrize("task", ["a", "0", "m7-success", "a" * 40])
def test_a_good_task_id_is_accepted(task, cli):
    assert cli("start", task, "--", "verify").returncode == 0
    assert (cli.state_dir / f"{task}.json").is_file()


def _trace(name):
    return json.loads((TRACES / f"{name}.json").read_text(encoding="utf-8"))


def test_the_success_trace_has_one_repair_and_ends_approved(workflow_mod):
    trace = _trace("success")
    workflow_mod.validate_record(trace)
    assert (trace["task_id"], trace["state"], trace["attempts"]) == ("m7-success", "approved", 2)
    assert [e["event"] for e in trace["history"]] == ["plan_accepted", "implementation_done", "verifier_fail",
                                                      "repair_done", "verifier_pass", "approve"]
    assert trace["history"][-1]["actor"] == "human"


def test_the_exhaustion_trace_fails_three_times_and_ends_blocked(workflow_mod):
    trace = _trace("exhaustion")
    workflow_mod.validate_record(trace)
    assert (trace["state"], trace["blocked_reason"], trace["attempts"]) == ("blocked", "retry_exhausted", 3)
    verdicts = [e["verification"]["result"] for e in trace["history"] if e["actor"] == "verifier"]
    assert verdicts == ["FAIL", "FAIL", "FAIL"]


@pytest.mark.parametrize("name", ["success", "exhaustion"])
def test_a_trace_holds_no_home_folder(name):
    text = (TRACES / f"{name}.json").read_text(encoding="utf-8")
    assert not re.search(r"[A-Za-z]:[\\/]|/home/|/Users/", text)
