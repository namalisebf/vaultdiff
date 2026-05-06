"""Tests for vaultdiff.profiler."""
import pytest
from vaultdiff.differ import SecretDiff
from vaultdiff.profiler import PathProfile, profile_diff, profile_diffs, _category


def _diff(
    path="secret/app",
    changed=None,
    left_only=None,
    right_only=None,
    left_data=None,
    right_data=None,
):
    return SecretDiff(
        path=path,
        changed_keys=changed or [],
        only_in_left=left_only or [],
        only_in_right=right_only or [],
        left_data=left_data or {},
        right_data=right_data or {},
    )


def test_category_stable():
    assert _category(0.0) == "stable"


def test_category_moderate():
    assert _category(0.2) == "moderate"


def test_category_volatile():
    assert _category(0.5) == "volatile"
    assert _category(1.0) == "volatile"


def test_profile_diff_no_differences():
    d = _diff(left_data={"a": "1", "b": "2"}, right_data={"a": "1", "b": "2"})
    p = profile_diff(d)
    assert p.volatility == 0.0
    assert p.category == "stable"
    assert p.changed_keys == 0
    assert p.only_in_left == 0
    assert p.only_in_right == 0


def test_profile_diff_all_changed():
    d = _diff(
        changed=["a", "b"],
        left_data={"a": "1", "b": "2"},
        right_data={"a": "x", "b": "y"},
    )
    p = profile_diff(d)
    assert p.changed_keys == 2
    assert p.volatility == 1.0
    assert p.category == "volatile"


def test_profile_diff_partial_change():
    d = _diff(
        changed=["b"],
        left_data={"a": "1", "b": "old"},
        right_data={"a": "1", "b": "new"},
    )
    p = profile_diff(d)
    assert p.total_keys == 2
    assert p.changed_keys == 1
    assert pytest.approx(p.volatility, abs=1e-4) == 0.5


def test_profile_diff_only_in_left():
    d = _diff(
        left_only=["x"],
        left_data={"x": "gone"},
        right_data={},
    )
    p = profile_diff(d)
    assert p.only_in_left == 1
    assert p.volatility == 1.0


def test_profile_diff_to_dict_keys():
    d = _diff(left_data={"a": "1"}, right_data={"a": "1"})
    result = profile_diff(d).to_dict()
    assert set(result.keys()) == {
        "path", "total_keys", "changed_keys",
        "only_in_left", "only_in_right", "volatility", "category",
    }


def test_profile_diffs_sorted_by_volatility_desc():
    stable = _diff(path="s", left_data={"a": "1"}, right_data={"a": "1"})
    volatile = _diff(path="v", changed=["a"], left_data={"a": "old"}, right_data={"a": "new"})
    profiles = profile_diffs([stable, volatile])
    assert profiles[0].path == "v"
    assert profiles[1].path == "s"


def test_profile_diffs_empty():
    assert profile_diffs([]) == []
