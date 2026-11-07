"""The human gate: only a person approves or rejects, only then, and no one reports a verifier result by hand."""

import json
import sys

import pytest

BEFORE_APPROVAL = ("planning", "implementing", "verifying", "repairing")
VERIFIER_EVENTS = ("verifier_pass", "verifier_fail", "verifier_unverified")
PASSING = (sys.executable, "-c", "import sys; sys.exit(0)")


def _record(cli):
    return json.loads((cli.state_dir / "t1.json").read_text(encoding="utf-8"))


def _at_verifying(cli):
    assert cli("start", "t1", "--", *PASSING).returncode == 0
    assert cli("event", "t1", "plan_accepted").returncode == 0
    assert cli("event", "t1", "implementation_done", "--actor", "agent").returncode == 0


def _waiting_for_approval(cli):
    _at_verifying(cli)
    assert cli("verify", "t1").returncode == 0
    assert _record(cli)["state"] == "awaiting_approval"


@pytest.mark.parametrize("event", ["approve", "reject"])
@pytest.mark.parametrize("actor", ["agent", "verifier"])
def test_only_a_person_may_decide(event, actor, reach, workflow_mod):
    with pytest.raises(workflow_mod.InvalidTransition):
        workflow_mod.apply_event(reach("awaiting_approval"), event, actor)


@pytest.mark.parametrize("event", ["approve", "reject"])
@pytest.mark.parametrize("state", [*BEFORE_APPROVAL, "approved", "blocked"])
def test_a_decision_is_refused_outside_awaiting_approval(state, event, reach, workflow_mod):
    with pytest.raises(workflow_mod.InvalidTransition):
        workflow_mod.apply_event(reach(state), event, "human")


def test_approve_ends_approved_and_names_the_person(reach, workflow_mod):
    record = workflow_mod.apply_event(reach("awaiting_approval"), "approve", "human", note="diff read")
    assert (record["state"], record["blocked_reason"]) == ("approved", None)
    assert (record["history"][-1]["actor"], record["history"][-1]["note"]) == ("human", "diff read")


def test_reject_ends_blocked_as_rejected_by_human(reach, workflow_mod):
    record = workflow_mod.apply_event(reach("awaiting_approval"), "reject", "human", note="wrong file")
    assert (record["state"], record["blocked_reason"]) == ("blocked", "rejected_by_human")
    assert record["history"][-1]["actor"] == "human"


def test_approve_on_the_command_line_defaults_to_the_human_actor(cli):
    _waiting_for_approval(cli)
    assert cli("event", "t1", "approve", "--note", "diff read").returncode == 0
    record = _record(cli)
    assert record["state"] == "approved" and record["history"][-1]["actor"] == "human"


def test_reject_on_the_command_line_blocks_the_task(cli):
    _waiting_for_approval(cli)
    assert cli("event", "t1", "reject", "--note", "why").returncode == 0
    assert _record(cli)["blocked_reason"] == "rejected_by_human"


@pytest.mark.parametrize("event", ["approve", "reject"])
def test_the_agent_cannot_decide_on_the_command_line(event, cli):
    _waiting_for_approval(cli)
    before = (cli.state_dir / "t1.json").read_bytes()
    done = cli("event", "t1", event, "--actor", "agent")
    assert done.returncode == 3 and done.stderr.strip()
    assert (cli.state_dir / "t1.json").read_bytes() == before


@pytest.mark.parametrize("event", VERIFIER_EVENTS)
@pytest.mark.parametrize("actor", ["human", "agent"])
def test_a_verifier_result_cannot_be_sent_by_hand(event, actor, cli):
    _at_verifying(cli)
    before = (cli.state_dir / "t1.json").read_bytes()
    done = cli("event", "t1", event, "--actor", actor)
    assert done.returncode == 3 and "verify" in done.stderr
    assert (cli.state_dir / "t1.json").read_bytes() == before


@pytest.mark.parametrize("event", VERIFIER_EVENTS)
@pytest.mark.parametrize("actor", ["human", "agent"])
def test_a_verifier_event_needs_the_verifier_actor(event, actor, reach, workflow_mod):
    with pytest.raises(workflow_mod.InvalidTransition):
        workflow_mod.apply_event(reach("verifying"), event, actor,
                                 verification={"exit_code": 0, "result": "PASS", "reason": "claimed"})


def test_the_actor_verifier_is_not_on_offer_on_the_command_line(cli):
    assert cli("start", "t1", "--", *PASSING).returncode == 0
    assert cli("event", "t1", "plan_accepted", "--actor", "verifier").returncode == 2
