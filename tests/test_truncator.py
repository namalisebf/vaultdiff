"""Tests for vaultdiff.truncator."""
import pytest
from vaultdiff.differ import SecretDiff
from vaultdiff.truncator import (
    TruncateConfig,
    TruncatedDiff,
    TruncateReport,
    truncate_diffs,
)


def _diff(path="secret/app", changed=None, left=None, right=None) -> SecretDiff:
    return SecretDiff(
        path=path,
        changed_keys=changed or [],
        only_in_left=left or [],
        only_in_right=right or [],
    )


def test_truncate_config_from_dict_defaults():
    cfg = TruncateConfig.from_dict({})
    assert cfg.max_changed_keys is None
    assert cfg.max_only_in_left is None
    assert cfg.max_only_in_right is None


def test_truncate_config_from_dict_values():
    cfg = TruncateConfig.from_dict(
        {"max_changed_keys": 2, "max_only_in_left": 1, "max_only_in_right": 3}
    )
    assert cfg.max_changed_keys == 2
    assert cfg.max_only_in_left == 1
    assert cfg.max_only_in_right == 3


def test_no_config_keeps_all_keys():
    d = _diff(changed=["a", "b", "c"], left=["x"], right=["y", "z"])
    report = truncate_diffs([d], TruncateConfig())
    assert len(report.entries) == 1
    entry = report.entries[0]
    assert entry.changed_keys == ["a", "b", "c"]
    assert entry.only_in_left == ["x"]
    assert entry.only_in_right == ["y", "z"]
    assert entry.truncated_changed == 0
    assert entry.truncated_left == 0
    assert entry.truncated_right == 0


def test_max_changed_keys_limits_and_counts_dropped():
    d = _diff(changed=["a", "b", "c", "d"])
    report = truncate_diffs([d], TruncateConfig(max_changed_keys=2))
    entry = report.entries[0]
    assert entry.changed_keys == ["a", "b"]
    assert entry.truncated_changed == 2


def test_max_only_in_left_limits_correctly():
    d = _diff(left=["x", "y", "z"])
    report = truncate_diffs([d], TruncateConfig(max_only_in_left=1))
    entry = report.entries[0]
    assert entry.only_in_left == ["x"]
    assert entry.truncated_left == 2


def test_max_only_in_right_limits_correctly():
    d = _diff(right=["p", "q"])
    report = truncate_diffs([d], TruncateConfig(max_only_in_right=1))
    entry = report.entries[0]
    assert entry.only_in_right == ["p"]
    assert entry.truncated_right == 1


def test_total_truncated_sums_across_entries():
    diffs = [
        _diff(changed=["a", "b", "c"]),
        _diff(path="secret/other", left=["x", "y"]),
    ]
    report = truncate_diffs(diffs, TruncateConfig(max_changed_keys=1, max_only_in_left=0))
    assert report.total_truncated() == 2 + 2


def test_has_differences_false_when_all_empty():
    entry = TruncatedDiff(
        path="p", changed_keys=[], only_in_left=[], only_in_right=[]
    )
    assert not entry.has_differences()


def test_has_differences_true_when_changed():
    entry = TruncatedDiff(
        path="p", changed_keys=["k"], only_in_left=[], only_in_right=[]
    )
    assert entry.has_differences()


def test_to_dict_structure():
    d = _diff(changed=["a", "b", "c"])
    report = truncate_diffs([d], TruncateConfig(max_changed_keys=2))
    result = report.to_dict()
    assert "entries" in result
    assert result["total_truncated"] == 1
    entry_dict = result["entries"][0]
    assert entry_dict["truncated_changed"] == 1
    assert entry_dict["path"] == "secret/app"


def test_empty_diffs_returns_empty_report():
    report = truncate_diffs([], TruncateConfig(max_changed_keys=5))
    assert report.entries == []
    assert report.total_truncated() == 0
