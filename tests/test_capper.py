"""Tests for vaultdiff.capper."""
import pytest
from vaultdiff.capper import CapConfig, CappedDiff, cap_diffs
from vaultdiff.differ import SecretDiff


def _diff(path="secret/app", changed=None, left=None, right=None):
    d = SecretDiff(path=path)
    d.changed_keys = list(changed or [])
    d.only_in_left = list(left or [])
    d.only_in_right = list(right or [])
    return d


def test_cap_config_from_dict_defaults():
    cfg = CapConfig.from_dict({})
    assert cfg.max_changed_keys is None
    assert cfg.max_only_in_left is None
    assert cfg.max_only_in_right is None


def test_cap_config_from_dict_values():
    cfg = CapConfig.from_dict({"max_changed_keys": 3, "max_only_in_left": 1})
    assert cfg.max_changed_keys == 3
    assert cfg.max_only_in_left == 1
    assert cfg.max_only_in_right is None


def test_cap_no_config_keeps_all():
    diff = _diff(changed=["a", "b", "c"], left=["x"], right=["y", "z"])
    report = cap_diffs([diff], CapConfig())
    assert len(report.entries) == 1
    entry = report.entries[0]
    assert entry.changed_keys == ["a", "b", "c"]
    assert entry.only_in_left == ["x"]
    assert entry.only_in_right == ["y", "z"]
    assert entry.dropped_changed == 0
    assert entry.dropped_left == 0
    assert entry.dropped_right == 0


def test_cap_changed_keys_limits_and_counts_dropped():
    diff = _diff(changed=["a", "b", "c", "d"])
    report = cap_diffs([diff], CapConfig(max_changed_keys=2))
    entry = report.entries[0]
    assert len(entry.changed_keys) == 2
    assert entry.dropped_changed == 2


def test_cap_only_in_left_limits():
    diff = _diff(left=["x", "y", "z"])
    report = cap_diffs([diff], CapConfig(max_only_in_left=1))
    entry = report.entries[0]
    assert len(entry.only_in_left) == 1
    assert entry.dropped_left == 2


def test_cap_only_in_right_limits():
    diff = _diff(right=["p", "q"])
    report = cap_diffs([diff], CapConfig(max_only_in_right=0))
    entry = report.entries[0]
    assert entry.only_in_right == []
    assert entry.dropped_right == 2


def test_cap_empty_list_returns_empty_report():
    report = cap_diffs([], CapConfig(max_changed_keys=5))
    assert report.total_paths == 0
    assert report.total_dropped == 0


def test_cap_report_total_dropped_sums_all_entries():
    d1 = _diff(changed=["a", "b", "c"])
    d2 = _diff(left=["x", "y"])
    report = cap_diffs([d1, d2], CapConfig(max_changed_keys=1, max_only_in_left=0))
    assert report.total_dropped == 2 + 2


def test_capped_diff_has_differences_true_when_changed():
    entry = CappedDiff(path="p", changed_keys=["k"], only_in_left=[], only_in_right=[])
    assert entry.has_differences() is True


def test_capped_diff_has_differences_false_when_clean():
    entry = CappedDiff(path="p", changed_keys=[], only_in_left=[], only_in_right=[])
    assert entry.has_differences() is False


def test_cap_report_to_dict_structure():
    diff = _diff(changed=["a"])
    report = cap_diffs([diff], CapConfig())
    d = report.to_dict()
    assert "total_paths" in d
    assert "total_dropped" in d
    assert "entries" in d
    assert d["entries"][0]["path"] == "secret/app"
