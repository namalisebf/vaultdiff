"""Unit tests for vaultdiff.collector."""
from __future__ import annotations

from vaultdiff.differ import SecretDiff
from vaultdiff.collector import CollectedEntry, CollectionReport, collect_diffs


def _diff(path, changed=None, left=None, right=None):
    return SecretDiff(
        path=path,
        changed_keys=changed or {},
        only_in_left=left or {},
        only_in_right=right or {},
    )


def test_collect_empty_list_returns_empty_report():
    report = collect_diffs([])
    assert report.total_paths == 0
    assert report.dirty_paths == 0
    assert report.clean_paths == 0
    assert report.entries == []


def test_collect_single_clean_diff():
    report = collect_diffs([_diff("secret/app")])
    assert report.total_paths == 1
    assert report.dirty_paths == 0
    assert report.clean_paths == 1
    entry = report.entries[0]
    assert not entry.has_differences()
    assert entry.path == "secret/app"


def test_collect_single_dirty_diff_changed_keys():
    report = collect_diffs([_diff("secret/app", changed={"key": ("a", "b")})])
    assert report.dirty_paths == 1
    entry = report.entries[0]
    assert entry.changed_keys == 1
    assert entry.only_in_left == 0
    assert entry.only_in_right == 0
    assert entry.has_differences()


def test_collect_only_in_left():
    report = collect_diffs([_diff("secret/app", left={"removed": "v"})])
    entry = report.entries[0]
    assert entry.only_in_left == 1
    assert entry.has_differences()


def test_collect_only_in_right():
    report = collect_diffs([_diff("secret/app", right={"added": "v"})])
    entry = report.entries[0]
    assert entry.only_in_right == 1
    assert entry.has_differences()


def test_collect_multiple_diffs_counts_correctly():
    diffs = [
        _diff("secret/a"),
        _diff("secret/b", changed={"x": ("1", "2")}),
        _diff("secret/c", left={"gone": "v"}, right={"new": "v"}),
    ]
    report = collect_diffs(diffs)
    assert report.total_paths == 3
    assert report.dirty_paths == 2
    assert report.clean_paths == 1


def test_collected_entry_to_dict_keys():
    entry = CollectedEntry(
        path="secret/x",
        changed_keys=2,
        only_in_left=1,
        only_in_right=0,
        total_keys=3,
    )
    d = entry.to_dict()
    assert d["path"] == "secret/x"
    assert d["changed_keys"] == 2
    assert d["only_in_left"] == 1
    assert d["only_in_right"] == 0
    assert d["total_keys"] == 3
    assert d["has_differences"] is True


def test_collection_report_to_dict_structure():
    report = collect_diffs([_diff("secret/a")])
    d = report.to_dict()
    assert "total_paths" in d
    assert "dirty_paths" in d
    assert "clean_paths" in d
    assert "entries" in d
    assert isinstance(d["entries"], list)


def test_total_keys_sums_all_categories():
    report = collect_diffs([
        _diff("p", changed={"a": ("1", "2")}, left={"b": "v"}, right={"c": "v"})
    ])
    entry = report.entries[0]
    assert entry.total_keys == 3
