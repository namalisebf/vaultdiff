"""Integration-style tests for profiler using real SecretDiff objects."""
from vaultdiff.differ import SecretDiff
from vaultdiff.profiler import profile_diffs, PathProfile


def _make_diff(path, left, right, changed=None, left_only=None, right_only=None):
    return SecretDiff(
        path=path,
        changed_keys=changed or [],
        only_in_left=left_only or [],
        only_in_right=right_only or [],
        left_data=left,
        right_data=right,
    )


def test_all_stable_paths_sorted_last():
    diffs = [
        _make_diff("a", {"k": "1"}, {"k": "1"}),
        _make_diff("b", {"k": "1"}, {"k": "1"}),
    ]
    profiles = profile_diffs(diffs)
    assert all(p.category == "stable" for p in profiles)


def test_volatile_path_sorts_first():
    stable = _make_diff("stable", {"a": "1", "b": "2"}, {"a": "1", "b": "2"})
    volatile = _make_diff(
        "volatile",
        {"x": "old", "y": "old"},
        {"x": "new", "y": "new"},
        changed=["x", "y"],
    )
    profiles = profile_diffs([stable, volatile])
    assert profiles[0].path == "volatile"
    assert profiles[0].volatility == 1.0


def test_profile_is_dataclass_instance():
    d = _make_diff("p", {"a": "1"}, {"a": "1"})
    p = profile_diffs([d])[0]
    assert isinstance(p, PathProfile)


def test_mixed_change_types_aggregate_correctly():
    d = _make_diff(
        "mixed",
        left={"a": "1", "b": "2", "c": "3"},
        right={"a": "X", "b": "2", "d": "4"},
        changed=["a"],
        left_only=["c"],
        right_only=["d"],
    )
    p = profile_diffs([d])[0]
    assert p.changed_keys == 1
    assert p.only_in_left == 1
    assert p.only_in_right == 1
    # total: a(changed)+b(unchanged)+c(left_only)+d(right_only) = 4
    assert p.total_keys == 4
    assert p.volatility == 3 / 4
    assert p.category == "volatile"


def test_to_dict_volatility_rounded():
    d = _make_diff(
        "p",
        left={"a": "1", "b": "2", "c": "3"},
        right={"a": "X", "b": "2", "c": "3"},
        changed=["a"],
    )
    result = profile_diffs([d])[0].to_dict()
    # volatility = 1/3, rounded to 4 decimal places
    assert result["volatility"] == round(1 / 3, 4)
