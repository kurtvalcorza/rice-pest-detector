from pathlib import Path

import pytest

from rice_pest_detector.labels import Box, load_label_file, parse_labels, validate_boxes


def test_parse_labels_reads_yolo_rows():
    text = "2 0.66171875 0.7140625 0.06171875 0.06484375\n3 0.1 0.2 0.05 0.05\n\n"
    assert parse_labels(text) == [
        Box(2, 0.66171875, 0.7140625, 0.06171875, 0.06484375),
        Box(3, 0.1, 0.2, 0.05, 0.05),
    ]


def test_parse_labels_rejects_wrong_field_count():
    with pytest.raises(ValueError, match="line 1"):
        parse_labels("2 0.5 0.5 0.1\n")


@pytest.mark.parametrize(
    ("box", "fragment"),
    [
        (Box(4, 0.5, 0.5, 0.1, 0.1), "class"),
        (Box(0, 0.5, 0.5, 0.0, 0.1), "area"),
        (Box(0, 0.98, 0.5, 0.1, 0.1), "outside"),
    ],
)
def test_validate_boxes_reports_each_problem(box, fragment):
    errors = validate_boxes([box])
    assert len(errors) == 1 and fragment in errors[0]


def test_validate_boxes_accepts_edge_touching_box():
    assert validate_boxes([Box(1, 0.05, 0.5, 0.1, 0.2)]) == []


def test_missing_label_file_is_an_error_not_an_empty_image(tmp_path: Path):
    with pytest.raises(FileNotFoundError):
        load_label_file(tmp_path / "absent.txt")


def test_parse_labels_converts_polygon_to_bounding_box():
    (box,) = parse_labels("1 0.2 0.2 0.6 0.2 0.4 0.8\n")
    assert (box.class_id, box.cx, box.cy, box.w, box.h) == pytest.approx((1, 0.4, 0.5, 0.4, 0.6))


def test_parse_labels_handles_mixed_box_and_polygon_rows():
    text = "0 0.5 0.5 0.1 0.1\n3 0.2 0.2 0.6 0.2 0.4 0.8\n"
    first, second = parse_labels(text)
    assert first == Box(0, 0.5, 0.5, 0.1, 0.1)
    assert (second.class_id, second.cx, second.cy, second.w, second.h) == pytest.approx((3, 0.4, 0.5, 0.4, 0.6))


@pytest.mark.parametrize("row", ["0 0.1 0.2 0.3 0.4 0.5", "0 0.1 0.2 0.3 0.4 0.5 0.6 0.7"])
def test_parse_labels_rejects_six_and_eight_field_rows(row):
    with pytest.raises(ValueError, match="line 2"):
        parse_labels("0 0.5 0.5 0.1 0.1\n" + row + "\n")


@pytest.mark.parametrize("field", ["cx", "cy", "w", "h"])
def test_non_finite_coordinates_are_rejected(field):
    values = {"cx": 0.5, "cy": 0.5, "w": 0.1, "h": 0.1, field: float("nan")}
    assert validate_boxes([Box(0, **values)]) == ["box 0: non-finite coordinate"]
    values[field] = float("inf")
    assert validate_boxes([Box(0, **values)]) == ["box 0: non-finite coordinate"]
