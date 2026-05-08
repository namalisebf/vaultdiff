"""Tests for vaultdiff.flattener."""
import pytest

from vaultdiff.differ import SecretDiff
from vaultdiff.flattener import FlatEntry, FlatReport, flatten_diffs


def _diff(
    path: str,
    changed=None,
    only_left=None,
    only_right=None,
) -> SecretDiff:
    return SecretDiff(
        path=path,
        changed_keys=changed or [],
        only_in_left=only_left or [],
        only_in_right=only_right or [],
    )


def test_flatten_empty_list_returns_empty_report():
    report = flatten_diffs([])
    assert report.total_paths == 0
    assert report.dirty_paths == 0
    assert report.entries == []


def test_flatten_single_clean_diff():
    report = flatten_diffs([_diff("secret/a")])
    assert report.total_paths == 1
    assert report.dirty_paths == 0
    entry = report.get("secret/a")
    assert entry is not None
    assert not entry.has_differences()


def test_flatten_single_dirty_diff():
    report = flatten_diffs([_diff("secret/a", changed=["key1"])])
    assert report.dirty_paths == 1
    entry = report.get("secret/a")
    assert entry.total_differences == 1
    assert entry.has_differences()


def test_flatten_multiple_distinct_paths():
    diffs = [
        _diff("secret/a", changed=["x"]),
        _diff("secret/b", only_left=["y"]),
        _diff("secret/c"),
    ]
    report = flatten_diffs(diffs)
    assert report.total_paths == 3
    assert report.dirty_paths == 2


def test_flatten_merges_duplicate_paths():
    diffs = [
        _diff("secret/a", changed=["k1"]),
        _diff("secret/a", only_left=["k2"]),
    ]
    report = flatten_diffs(diffs)
    assert report.total_paths == 1
    entry = report.get("secret/a")
    assert "k1" in entry.changed_keys
    assert "k2" in entry.only_in_left
    assert entry.total_differences == 2


def test_flatten_deduplicates_keys_within_merged_path():
    diffs = [
        _diff("secret/a", changed=["k1"]),
        _diff("secret/a", changed=["k1", "k2"]),
    ]
    report = flatten_diffs(diffs)
    entry = report.get("secret/a")
    assert entry.changed_keys.count("k1") == 1
    assert "k2" in entry.changed_keys
    assert entry.total_differences == 2


def test_flat_entry_to_dict_keys():
    entry = FlatEntry(
        path="secret/x",
        changed_keys=["a"],
        only_in_left=[],
        only_in_right=["b"],
        total_differences=2,
    )
    d = entry.to_dict()
    assert set(d.keys()) == {
        "path", "changed_keys", "only_in_left", "only_in_right",
        "total_differences", "has_differences",
    }
    assert d["has_differences"] is True


def test_flat_report_to_dict_structure():
    report = flatten_diffs([_diff("secret/a", changed=["k"])])
    d = report.to_dict()
    assert d["total_paths"] == 1
    assert d["dirty_paths"] == 1
    assert len(d["entries"]) == 1


def test_flat_report_get_returns_none_for_missing_path():
    report = flatten_diffs([_diff("secret/a")])
    assert report.get("secret/missing") is None
