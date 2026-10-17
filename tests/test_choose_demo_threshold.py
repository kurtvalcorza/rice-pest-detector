import pytest

from tools.choose_demo_threshold import GRID, choose_threshold, sweep


def det(cls, score):
    return {"class_id": cls, "score": score}


# Two validation images: truth RBB 2 / WSB 0, and RBB 0 / WSB 1. Scores sit low (0.3-0.45),
# like run r18-1, plus noise at 0.1 that a too-low threshold would count.
IMAGES = [
    {"refs": {"RBB": 2, "WSB": 0}, "dets": [det(0, 0.45), det(1, 0.31), det(2, 0.1)]},
    {"refs": {"RBB": 0, "WSB": 1}, "dets": [det(3, 0.40), det(0, 0.1)]},
]


def test_sweep_reports_count_errors_per_threshold():
    rows = {r["threshold"]: r for r in sweep(IMAGES, [0.05, 0.3, 0.5])}
    assert rows[0.3]["mae_total"] == 0.0           # counts exactly right
    assert rows[0.05]["mae_total"] == pytest.approx(1.0)  # noise counted: +1 error on each image
    assert rows[0.5]["mae_total"] == pytest.approx(1.5)   # nothing kept: RBB 2/2, WSB 1/2
    assert rows[0.5]["detections_kept"] == 0
    assert set(rows[0.3]) >= {"count_accuracy", "count_errors", "detections_kept"}


def test_choose_takes_the_lowest_error_and_prefers_the_higher_threshold_on_ties():
    best, rows = choose_threshold(IMAGES, [0.2, 0.25, 0.3, 0.5])
    assert best == 0.3  # 0.2, 0.25 and 0.3 all give 0 error; the highest is chosen
    assert [r["threshold"] for r in rows] == [0.2, 0.25, 0.3, 0.5]


def test_default_grid_spans_low_scores_and_includes_the_shipping_threshold():
    assert min(GRID) <= 0.05 and 0.5 in GRID and GRID == sorted(GRID)
