"""All 56 state-event pairs: the 8 allowed reach their state, the 48 others change nothing."""

import copy
import itertools

import pytest

STATES = ("planning", "implementing", "verifying", "repairing", "awaiting_approval", "approved", "blocked")
EVENTS = ("plan_accepted", "implementation_done", "repair_done", "verifier_pass", "verifier_fail",
          "verifier_unverified", "approve", "reject")
ALLOWED = {
    ("planning", "plan_accepted"): "implementing",
    ("implementing", "implementation_done"): "verifying",
    ("verifying", "verifier_pass"): "awaiting_approval",
    ("verifying", "verifier_fail"): "repairing",
    ("verifying", "verifier_unverified"): "blocked",
    ("repairing", "repair_done"): "verifying",
    ("awaiting_approval", "approve"): "approved",
    ("awaiting_approval", "reject"): "blocked",
}
ALL_PAIRS = list(itertools.product(STATES, EVENTS))
REJECTED = [pair for pair in ALL_PAIRS if pair not in ALLOWED]


def test_there_are_56_pairs_8_allowed_and_48_rejected():
    assert (len(ALL_PAIRS), len(ALLOWED), len(REJECTED)) == (56, 8, 48)


def test_the_states_and_events_match_the_contract(workflow_mod):
    assert tuple(workflow_mod.STATES) == STATES
    assert tuple(workflow_mod.EVENTS) == EVENTS
    assert set(workflow_mod.TERMINAL) == {"approved", "blocked"}


def test_the_table_is_data_with_nine_rows(workflow_mod):
    assert len(workflow_mod.TRANSITIONS) == 9
    assert {(row.source, row.event) for row in workflow_mod.TRANSITIONS} == set(ALLOWED)


@pytest.mark.parametrize(("state", "event"), list(ALLOWED))
def test_an_allowed_pair_reaches_its_state(state, event, reach, send):
    assert send(reach(state), event)["state"] == ALLOWED[state, event]


@pytest.mark.parametrize(("state", "event"), REJECTED)
def test_a_rejected_pair_raises_and_leaves_the_record_unchanged(state, event, reach, send, workflow_mod):
    record = reach(state)
    before = copy.deepcopy(record)
    with pytest.raises(workflow_mod.InvalidTransition):
        send(record, event)
    assert record == before


def test_applying_an_event_appends_one_entry_and_leaves_the_input_alone(reach, send):
    record = reach("implementing")
    before = copy.deepcopy(record)
    after = send(record, "implementation_done")
    assert record == before
    assert after["history"][:-1] == before["history"] and len(after["history"]) == len(before["history"]) + 1
    entry = after["history"][-1]
    assert (entry["seq"], entry["actor"], entry["event"]) == (2, "agent", "implementation_done")
    assert (entry["from"], entry["to"]) == ("implementing", "verifying")
    assert entry["attempt"] is None and entry["verification"] is None and entry["note"] is None


@pytest.mark.parametrize(("state", "event", "actor"), [
    ("planning", "plan_accepted", "agent"),
    ("planning", "plan_accepted", "verifier"),
    ("implementing", "implementation_done", "verifier"),
    ("repairing", "repair_done", "verifier"),
])
def test_an_allowed_pair_from_the_wrong_actor_is_rejected(state, event, actor, reach, workflow_mod):
    with pytest.raises(workflow_mod.InvalidTransition):
        workflow_mod.apply_event(reach(state), event, actor)


@pytest.mark.parametrize("actor", ["human", "agent"])
def test_a_person_or_the_agent_may_say_the_work_is_done(actor, reach, workflow_mod):
    assert workflow_mod.apply_event(reach("implementing"), "implementation_done", actor)["state"] == "verifying"
    assert workflow_mod.apply_event(reach("repairing"), "repair_done", actor)["state"] == "verifying"
