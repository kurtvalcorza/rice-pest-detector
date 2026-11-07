"""The saved per-image differences (new minus reference) of the four dense-tray comparisons."""
import json

import pytest

from tools.dense_tray_bootstrap import main, paired_bootstrap

CASES = [
    ([-19, 5, -7, -8, 0, 1, -1, -1, 7, -21, -9, -9, -9, -2, 0, 9, -3, -3], (-136 / 18, -8 / 18), True),
    ([-3, -1, -30, -10, -4, -2, -6, -3, -6, 8, 1, 0, 2, -2, 4, 1, -3, -4], (-129 / 18, -3 / 18), True),
    ([3, 0, 16, 0, 0, -1, 2, 1, 5, -4, -1, 1, 0, 1, -3, -1, 0, -3], (-13 / 18, 56 / 18), False),
    ([0, -1, -4, 1, 3, 0, 4, -1, -1, -2, -1, 1, -1, 0, 0, -1, 0, 1], (-16 / 18, 13 / 18), False),
]


@pytest.mark.parametrize("diff, interval, better", CASES)
def test_the_stored_intervals_are_reproduced_exactly(diff, interval, better):
    result = paired_bootstrap([0] * len(diff), diff)
    assert result["ci95"] == pytest.approx(interval)
    assert result["new_is_better"] is better


def test_the_pairs_must_match():
    with pytest.raises(ValueError, match="same photos"):
        paired_bootstrap([1, 2], [1])
    with pytest.raises(ValueError, match="same photos"):
        paired_bootstrap([], [])


def test_the_command_checks_a_saved_report(tmp_path, capsys):
    diff, interval, _ = CASES[0]
    report = {"ref_abs_err": [0] * 18, "new_abs_err": diff, "ci95": list(interval), "resamples": 10000, "seed": 20261017}
    path = tmp_path / "report.json"
    path.write_text(json.dumps(report), encoding="utf-8")
    assert main([str(path)]) == 0
    assert "matches" in capsys.readouterr().out
    path.write_text(json.dumps({**report, "ci95": [0.0, 1.0]}), encoding="utf-8")
    assert main([str(path)]) == 1
