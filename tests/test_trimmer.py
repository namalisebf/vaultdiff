"""Tests for vaultdiff.trimmer."""
import pytest

from vaultdiff.differ import SecretDiff
from vaultdiff.trimmer import TrimConfig, TrimmedResult, trim_diffs


def _diff(path: str, changed=None, only_left=None, only_right=None) -> SecretDiff:
    return SecretDiff(
        path=path,
        changed=changed or {},
        only_in_left=only_left or {},
        only_in_right=only_right or {},
    )


def test_trim_no_config_keeps_all():
    diffs = [_diff("a"), _diff("b"), _diff("c")]
    result = trim_diffs(diffs, TrimConfig())
    assert len(result.kept) == 3
    assert len(result.dropped) == 0
    assert result.total == 3


def test_trim_exclude_clean_removes_no_difference_diffs():
    diffs = [
        _diff("clean"),
        _diff("dirty", changed={"k": ("a", "b")}),
    ]
    result = trim_diffs(diffs, TrimConfig(exclude_clean=True))
    assert len(result.kept) == 1
    assert result.kept[0].path == "dirty"
    assert len(result.dropped) == 1


def test_trim_min_changed_keys_filters_below_threshold():
    diffs = [
        _diff("one", changed={"k": ("a", "b")}),
        _diff("two", changed={"k1": ("a", "b"), "k2": ("c", "d")}),
        _diff("zero"),
    ]
    result = trim_diffs(diffs, TrimConfig(min_changed_keys=2))
    assert len(result.kept) == 1
    assert result.kept[0].path == "two"
    assert len(result.dropped) == 2


def test_trim_max_paths_limits_output():
    diffs = [_diff(f"path/{i}", changed={"k": ("a", "b")}) for i in range(5)]
    result = trim_diffs(diffs, TrimConfig(max_paths=3))
    assert len(result.kept) == 3
    assert len(result.dropped) == 2
    assert result.total == 5


def test_trim_only_in_left_threshold():
    diffs = [
        _diff("few", only_left={"k": "v"}),
        _diff("many", only_left={"k1": "v1", "k2": "v2"}),
    ]
    result = trim_diffs(diffs, TrimConfig(only_in_left_threshold=2))
    assert len(result.kept) == 1
    assert result.kept[0].path == "many"


def test_trim_only_in_right_threshold():
    diffs = [
        _diff("none"),
        _diff("some", only_right={"x": "1", "y": "2", "z": "3"}),
    ]
    result = trim_diffs(diffs, TrimConfig(only_in_right_threshold=3))
    assert len(result.kept) == 1
    assert result.kept[0].path == "some"


def test_trimmed_result_to_dict():
    diffs = [
        _diff("keep", changed={"k": ("a", "b")}),
        _diff("drop"),
    ]
    result = trim_diffs(diffs, TrimConfig(exclude_clean=True))
    d = result.to_dict()
    assert d["kept"] == 1
    assert d["dropped"] == 1
    assert d["total"] == 2
    assert "keep" in d["paths"]


def test_max_paths_applied_after_threshold_filter():
    diffs = [
        _diff("a", changed={"k": ("1", "2")}),
        _diff("b"),
        _diff("c", changed={"k": ("1", "2")}),
        _diff("d", changed={"k": ("1", "2")}),
    ]
    result = trim_diffs(diffs, TrimConfig(exclude_clean=True, max_paths=2))
    assert len(result.kept) == 2
    assert len(result.dropped) == 2
