"""read_report: counts from a JUnit XML report, or None when there is no trustworthy report."""

TWO_SUITES = """<?xml version="1.0" encoding="utf-8"?>
<testsuites>
  <testsuite name="a" tests="3" failures="1" errors="0" skipped="1">
    <testcase classname="tests.test_a" name="test_ok"/>
    <testcase classname="tests.test_a" name="test_broken"><failure message="assert 1 == 2"/></testcase>
    <testcase classname="tests.test_a" name="test_later"><skipped message="not today"/></testcase>
  </testsuite>
  <testsuite name="b" tests="2" failures="0" errors="1" skipped="0">
    <testcase classname="tests.test_b" name="test_ok"/>
    <testcase classname="tests.test_b" name="test_setup"><error message="fixture crashed"/></testcase>
  </testsuite>
</testsuites>
"""

ONE_SUITE_ROOT = """<testsuite name="pytest" tests="4" failures="0" errors="0" skipped="0">
  <testcase classname="tests.test_infer" name="test_one"/>
  <testcase classname="tests.test_infer" name="test_two"/>
  <testcase classname="tests.test_infer" name="test_three"/>
  <testcase classname="tests.test_infer" name="test_four"/>
</testsuite>
"""


def _write(tmp_path, text, name="junit.xml"):
    path = tmp_path / name
    path.write_text(text, encoding="utf-8")
    return path


def test_counts_are_summed_over_every_testsuite(verify_mod, tmp_path):
    report = verify_mod.read_report(_write(tmp_path, TWO_SUITES))
    assert (report.tests, report.failures, report.errors, report.skipped) == (5, 1, 1, 1)


def test_failed_tests_names_each_failure_and_error(verify_mod, tmp_path):
    report = verify_mod.read_report(_write(tmp_path, TWO_SUITES))
    assert report.failed_tests == ["tests.test_a::test_broken", "tests.test_b::test_setup"]


def test_a_single_testsuite_root_is_read(verify_mod, tmp_path):
    report = verify_mod.read_report(_write(tmp_path, ONE_SUITE_ROOT))
    assert (report.tests, report.failures, report.errors, report.skipped) == (4, 0, 0, 0)
    assert report.failed_tests == []


def test_failed_tests_are_capped_at_twenty(verify_mod, tmp_path):
    cases = "".join(f'<testcase classname="t" name="test_{i}"><failure/></testcase>' for i in range(25))
    xml = f'<testsuites><testsuite tests="25" failures="25" errors="0" skipped="0">{cases}</testsuite></testsuites>'
    report = verify_mod.read_report(_write(tmp_path, xml))
    assert report.failures == 25 and len(report.failed_tests) == 20


def test_a_missing_report_gives_none(verify_mod, tmp_path):
    assert verify_mod.read_report(tmp_path / "nowhere.xml") is None


def test_malformed_xml_gives_none(verify_mod, tmp_path):
    assert verify_mod.read_report(_write(tmp_path, "<testsuites><testsuite tests='1'>")) is None


def test_xml_that_is_not_a_junit_report_gives_none(verify_mod, tmp_path):
    assert verify_mod.read_report(_write(tmp_path, "<html><body>4 passed</body></html>")) is None


def test_a_non_numeric_count_gives_none(verify_mod, tmp_path):
    xml = '<testsuite tests="many" failures="0" errors="0" skipped="0"/>'
    assert verify_mod.read_report(_write(tmp_path, xml)) is None
