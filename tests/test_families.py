import pytest

from rice_pest_detector.families import family_key


@pytest.mark.parametrize(
    ("name", "expected"),
    [
        ("20251107_151341_jpg.rf.2670f243bb64f0610976901250699dc7.jpg", "20251107_151341"),
        ("IMG_2652_JPG.rf.e9189f682cd38d9b9875bbd101974711.jpg", "img_2652"),
        ("IMG_2652_jpg.rf.0000000000000000000000000000abcd.jpg", "img_2652"),
        ("trap_a_png.rf.ab12.png", "trap_a"),
    ],
)
def test_family_key_extracts_source_stem(name, expected):
    assert family_key(name) == expected


@pytest.mark.parametrize("name", ["plain.jpg", "IMG_1.rf.jpg", "x_jpg.rf.ZZZ.jpg", ""])
def test_family_key_rejects_non_roboflow_names(name):
    with pytest.raises(ValueError, match="Roboflow"):
        family_key(name)
