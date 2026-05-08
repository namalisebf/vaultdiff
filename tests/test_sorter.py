"""Tests for vaultdiff.sorter."""
import pytest

from vaultdiff.differ import SecretDiff
from vaultdiff.sorter import SortConfig, SortKey, SortedReport, sort_diffs


def _diff(path: str, changed=0, only_left=0, only_right=0) -> SecretDiff:
    changed_keys = {f"k{i}": ("old", "new") for i in range(changed)}
    only_in_left = {f"l{i}": "v" for i in range(only_left)}
    only_in_right = {f"r{i}": "v" for i in range(only_right)}
    return SecretDiff(
        path=path,
        changed_keys=changed_keys,
        only_in_left=only_in_left,
        only_in_right=only_in_right,
    )


def test_sort_empty_list_returns_empty_report():
    report = sort_diffs([])
    assert report.total_paths == 0
    assert report.diffs == []


def test_sort_default_key_is_path():
    diffs = [_diff("z/secret"), _diff("a/secret"), _diff("m/secret")]
    report = sort_diffs(diffs)
    assert report.key == SortKey.PATH
    assert [d.path for d in report.diffs] == ["a/secret", "m/secret", "z/secret"]


def test_sort_path_reverse():
    diffs = [_diff("a/secret"), _diff("z/secret"), _diff("m/secret")]
    config = SortConfig(key=SortKey.PATH, reverse=True)
    report = sort_diffs(diffs, config)
    assert [d.path for d in report.diffs] == ["z/secret", "m/secret", "a/secret"]


def test_sort_by_changed_keys_ascending():
    diffs = [_diff("a", changed=3), _diff("b", changed=1), _diff("c", changed=2)]
    config = SortConfig(key=SortKey.CHANGED_KEYS, reverse=False)
    report = sort_diffs(diffs, config)
    assert [d.path for d in report.diffs] == ["b", "c", "a"]


def test_sort_by_changed_keys_descending():
    diffs = [_diff("a", changed=1), _diff("b", changed=5), _diff("c", changed=3)]
    config = SortConfig(key=SortKey.CHANGED_KEYS, reverse=True)
    report = sort_diffs(diffs, config)
    assert report.diffs[0].path == "b"
    assert report.diffs[-1].path == "a"


def test_sort_by_differences_counts_all_change_types():
    diffs = [
        _diff("x", changed=1, only_left=1, only_right=1),  # total=3
        _diff("y", changed=0, only_left=0, only_right=1),  # total=1
        _diff("z", changed=2, only_left=0, only_right=0),  # total=2
    ]
    config = SortConfig(key=SortKey.DIFFERENCES, reverse=True)
    report = sort_diffs(diffs, config)
    assert [d.path for d in report.diffs] == ["x", "z", "y"]


def test_sort_config_from_dict():
    config = SortConfig.from_dict({"key": "changed_keys", "reverse": True})
    assert config.key == SortKey.CHANGED_KEYS
    assert config.reverse is True


def test_sort_config_from_dict_empty():
    config = SortConfig.from_dict({})
    assert config.key == SortKey.PATH
    assert config.reverse is False


def test_sort_config_from_dict_invalid_key_falls_back_to_path():
    config = SortConfig.from_dict({"key": "nonexistent_key"})
    assert config.key == SortKey.PATH


def test_sorted_report_to_dict_structure():
    diffs = [_diff("a/b"), _diff("c/d")]
    report = sort_diffs(diffs)
    d = report.to_dict()
    assert "key" in d
    assert "reverse" in d
    assert "total_paths" in d
    assert "paths" in d
    assert d["total_paths"] == 2


def test_sorted_report_is_dataclass_instance():
    report = sort_diffs([_diff("p")])
    assert isinstance(report, SortedReport)
