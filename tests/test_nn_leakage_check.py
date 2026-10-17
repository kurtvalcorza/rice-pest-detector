from tools.nn_leakage_check import nearest_train_distances, summarize


def test_nearest_train_distance_and_summary():
    hashes = {"a": ("train", 0b0000), "b": ("train", 0xFFFF), "v1": ("val", 0b0011), "t1": ("test", 0xFFFF)}
    dist = nearest_train_distances(hashes)
    assert dist == {"val": {"v1": 2}, "test": {"t1": 0}}
    summary = summarize(dist)
    assert summary["val"] == {"families": 1, "min_distance": 2, "within_d2": 1, "within_d4": 1}
    assert summary["test"]["within_d2"] == 1
