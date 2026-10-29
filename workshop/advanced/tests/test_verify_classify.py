"""classify: rows 2-9 of the decision table in specs/004-advanced-workshop/contracts/verifier-cli.md.

The table is read top to bottom and the first matching row decides. PASS needs every signal to agree;
anything the verifier cannot positively confirm is UNVERIFIED (fail-closed).
"""

import pytest

PASS, FAIL, UNVERIFIED = ("PASS", 0), ("FAIL", 1), ("UNVERIFIED", 2)


@pytest.fixture
def counts(verify_mod):
    def make(tests=4, failures=0, errors=0, skipped=0, failed_tests=()):
        return verify_mod.ReportCounts(tests=tests, failures=failures, errors=errors, skipped=skipped,
                                       failed_tests=list(failed_tests))
    return make


def _decide(verify_mod, exit_code, report, min_tests=4, timed_out=False, started=True):
    result, code, reason = verify_mod.classify(exit_code, report, min_tests, timed_out, started)
    assert isinstance(reason, str) and reason
    return (result, code), reason


def test_row2_a_command_that_never_started_is_unverified(verify_mod, counts):
    assert _decide(verify_mod, None, None, started=False)[0] == UNVERIFIED


def test_row2_beats_a_report_left_lying_around(verify_mod, counts):
    assert _decide(verify_mod, None, counts(), started=False)[0] == UNVERIFIED


def test_row3_a_timeout_is_unverified_even_with_a_passing_report(verify_mod, counts):
    outcome, reason = _decide(verify_mod, None, counts(), timed_out=True)
    assert outcome == UNVERIFIED and "time" in reason.lower()


def test_row3_a_timeout_beats_a_failing_report(verify_mod, counts):
    assert _decide(verify_mod, None, counts(failures=1), timed_out=True)[0] == UNVERIFIED


def test_row4_no_readable_report_is_unverified_even_when_the_command_passed(verify_mod):
    outcome, reason = _decide(verify_mod, 0, None)
    assert outcome == UNVERIFIED and "report" in reason.lower()


def test_row5_a_failure_in_the_report_is_fail(verify_mod, counts):
    report = counts(failures=1, failed_tests=["tests.test_infer::test_preprocess_shape_range_and_no_normalisation"])
    outcome, reason = _decide(verify_mod, 1, report)
    assert outcome == FAIL
    assert "1 of 4" in reason and "test_preprocess_shape_range_and_no_normalisation" in reason


def test_row5_an_error_in_the_report_is_fail(verify_mod, counts):
    assert _decide(verify_mod, 1, counts(errors=1, failed_tests=["t::e"]))[0] == FAIL


def test_row5_a_failing_report_is_fail_even_when_the_command_exited_0(verify_mod, counts):
    assert _decide(verify_mod, 0, counts(failures=2, failed_tests=["t::a", "t::b"]))[0] == FAIL


def test_row6_a_failed_command_with_a_clean_report_is_unverified(verify_mod, counts):
    outcome, reason = _decide(verify_mod, 1, counts())
    assert outcome == UNVERIFIED and "1" in reason


def test_row7_zero_tests_is_unverified(verify_mod, counts):
    assert _decide(verify_mod, 0, counts(tests=0), min_tests=1)[0] == UNVERIFIED


def test_row7_every_test_skipped_is_unverified(verify_mod, counts):
    outcome, reason = _decide(verify_mod, 0, counts(tests=4, skipped=4))
    assert outcome == UNVERIFIED and "skip" in reason.lower()


def test_row8_fewer_tests_than_required_is_unverified(verify_mod, counts):
    outcome, reason = _decide(verify_mod, 0, counts(tests=3))
    assert outcome == UNVERIFIED and "3" in reason and "4" in reason


def test_row8_skipped_tests_do_not_count_towards_the_minimum(verify_mod, counts):
    assert _decide(verify_mod, 0, counts(tests=4, skipped=1))[0] == UNVERIFIED


def test_row9_everything_agrees_is_pass(verify_mod, counts):
    outcome, reason = _decide(verify_mod, 0, counts(tests=4))
    assert outcome == PASS and reason == "4 tests ran, 0 failed"


def test_row9_more_tests_than_required_is_pass(verify_mod, counts):
    assert _decide(verify_mod, 0, counts(tests=9, skipped=1))[0] == PASS


def test_classify_does_no_input_or_output(verify_mod, counts, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _decide(verify_mod, 0, counts())
    assert list(tmp_path.iterdir()) == []
