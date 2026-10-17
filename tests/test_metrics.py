import pytest

from rice_pest_detector.metrics import count_accuracy, count_within_tolerance, map50, species_counts


@pytest.mark.parametrize(
    ("pred", "ref", "ok"),
    [(0, 0, True), (1, 0, True), (2, 0, False), (10, 9, True), (11, 9, False),
     (22, 20, True), (23, 20, False), (18, 20, True), (17, 20, False)],
)
def test_count_within_tolerance(pred, ref, ok):
    assert count_within_tolerance(pred, ref) is ok


def test_species_counts_groups_sexes_and_reports_zero():
    assert species_counts([0, 1, 1]) == {"RBB": 3, "WSB": 0}


def test_count_accuracy_requires_every_species_to_pass():
    preds = [{"RBB": 3, "WSB": 0}, {"RBB": 3, "WSB": 5}]
    refs = [{"RBB": 3, "WSB": 0}, {"RBB": 3, "WSB": 1}]
    assert count_accuracy(preds, refs) == 0.5


def _gt():
    return {
        "images": [{"id": 1, "file_name": "a.jpg", "width": 100, "height": 100}],
        "annotations": [
            {"id": 1, "image_id": 1, "category_id": 1, "bbox": [10, 10, 20, 20], "area": 400, "iscrowd": 0},
            {"id": 2, "image_id": 1, "category_id": 3, "bbox": [60, 60, 20, 20], "area": 400, "iscrowd": 0},
        ],
        "categories": [{"id": i, "name": n} for i, n in
                       enumerate(["RBB_FEMALE", "RBB_MALE", "WSB_FEMALE", "WSB_MALE"], start=1)],
    }


def test_confusion_counts_sex_swaps_misses_and_spurious():
    from rice_pest_detector.metrics import confusion

    gt = [(0, [0, 0, 10, 10]), (2, [50, 50, 60, 60])]
    det = [(1, [0, 0, 10, 10]), (3, [80, 80, 90, 90])]
    assert confusion(gt, det) == {("RBB_FEMALE", "RBB_MALE"): 1, ("WSB_FEMALE", "missed"): 1,
                                  ("spurious", "WSB_MALE"): 1}


def test_map50_rewards_wrong_sex_only_when_grouped():
    dets = [{"image_id": 1, "category_id": 2, "bbox": [10, 10, 20, 20], "score": 0.9},
            {"image_id": 1, "category_id": 3, "bbox": [60, 60, 20, 20], "score": 0.9}]
    grouped = map50(_gt(), dets, group_species=True)
    assert grouped["all"] == pytest.approx(1.0)
    assert map50(_gt(), dets, group_species=False)["RBB_FEMALE"] == pytest.approx(0.0)


def test_count_errors_expose_what_the_tolerance_hides():
    from rice_pest_detector.metrics import count_errors
    refs = [{"RBB": 1, "WSB": 0}, {"RBB": 12, "WSB": 40}, {"RBB": 0, "WSB": 0}]
    zero = [{"RBB": 0, "WSB": 0}] * 3
    assert count_accuracy(zero, refs) == pytest.approx(2 / 3)  # the 1-insect image passes empty
    e = count_errors(zero, refs)
    assert e["RBB"]["mae"] == pytest.approx(13 / 3) and e["RBB"]["bias"] == pytest.approx(-13 / 3)
    assert e["RBB"]["exact"] == pytest.approx(1 / 3) and e["RBB"]["presence_recall"] == 0.0
    assert e["RBB"]["mae_by_density"] == {"1-9": {"images": 1, "mae": 1.0},
                                          "10-29": {"images": 1, "mae": 12.0},
                                          "30+": {"images": 0, "mae": None}}
    assert e["WSB"]["mae_by_density"]["30+"] == {"images": 1, "mae": 40.0}
    over = count_errors([{"RBB": 2, "WSB": 1}, {"RBB": 12, "WSB": 40}, {"RBB": 0, "WSB": 0}], refs)
    assert over["RBB"]["bias"] == pytest.approx(1 / 3) and over["RBB"]["presence_recall"] == 1.0
    assert over["WSB"]["presence_recall"] == 1.0 and over["WSB"]["exact"] == pytest.approx(2 / 3)
