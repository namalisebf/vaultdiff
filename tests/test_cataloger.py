"""Tests for vaultdiff.cataloger."""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from vaultdiff.differ import SecretDiff
from vaultdiff.cataloger import CatalogEntry, CatalogReport, catalog_diffs


def _diff(
    path="secret/app",
    changed=None,
    only_left=None,
    only_right=None,
):
    d = MagicMock(spec=SecretDiff)
    d.path = path
    d.changed_keys = changed or {}
    d.only_in_left = only_left or {}
    d.only_in_right = only_right or {}
    d.has_differences = bool(
        (changed or {}) or (only_left or {}) or (only_right or {})
    )
    return d


def test_catalog_empty_list_returns_empty_report():
    report = catalog_diffs([])
    assert report.total_paths == 0
    assert report.dirty_paths == 0
    assert report.entries == []


def test_catalog_single_clean_diff():
    report = catalog_diffs([_diff()])
    assert report.total_paths == 1
    assert report.dirty_paths == 0
    entry = report.entries[0]
    assert entry.path == "secret/app"
    assert entry.has_differences is False
    assert entry.changed_keys == 0
    assert entry.only_in_left == 0
    assert entry.only_in_right == 0


def test_catalog_dirty_diff_counted():
    report = catalog_diffs([
        _diff(changed={"DB_PASS": ("old", "new")})
    ])
    assert report.dirty_paths == 1
    entry = report.entries[0]
    assert entry.has_differences is True
    assert entry.changed_keys == 1


def test_catalog_only_in_left_counted():
    report = catalog_diffs([
        _diff(only_left={"LEGACY_KEY": "val"})
    ])
    entry = report.entries[0]
    assert entry.only_in_left == 1
    assert entry.only_in_right == 0
    assert entry.has_differences is True


def test_catalog_only_in_right_counted():
    report = catalog_diffs([
        _diff(only_right={"NEW_KEY": "val"})
    ])
    entry = report.entries[0]
    assert entry.only_in_right == 1
    assert entry.only_in_left == 0


def test_catalog_total_keys_union_of_both_sides():
    report = catalog_diffs([
        _diff(
            changed={"A": ("1", "2")},
            only_left={"B": "x"},
            only_right={"C": "y"},
        )
    ])
    entry = report.entries[0]
    # A in both sides, B left-only, C right-only => union = {A, B, C}
    assert entry.total_keys == 3


def test_catalog_tags_applied_from_map():
    tag_map = {"secret/app": ["critical", "production"]}
    report = catalog_diffs([_diff()], tags=tag_map)
    assert report.entries[0].tags == ["critical", "production"]


def test_catalog_missing_tags_default_empty():
    report = catalog_diffs([_diff()], tags={"other/path": ["x"]})
    assert report.entries[0].tags == []


def test_catalog_report_to_dict_structure():
    report = catalog_diffs([_diff(changed={"K": ("a", "b")})])
    d = report.to_dict()
    assert "total_paths" in d
    assert "dirty_paths" in d
    assert "entries" in d
    entry_d = d["entries"][0]
    assert "path" in entry_d
    assert "has_differences" in entry_d
    assert "tags" in entry_d


def test_catalog_multiple_paths_counted_correctly():
    diffs = [
        _diff(path="secret/a"),
        _diff(path="secret/b", changed={"X": ("1", "2")}),
        _diff(path="secret/c", only_right={"Y": "z"}),
    ]
    report = catalog_diffs(diffs)
    assert report.total_paths == 3
    assert report.dirty_paths == 2
