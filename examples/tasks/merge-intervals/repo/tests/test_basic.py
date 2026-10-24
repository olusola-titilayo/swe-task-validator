from intervals import merge_intervals


def test_empty():
    assert merge_intervals([]) == []


def test_sorted_overlapping():
    assert merge_intervals([[1, 3], [2, 6], [8, 10]]) == [[1, 6], [8, 10]]
