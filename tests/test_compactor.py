"""Tests for vaultdiff.compactor."""
from __future__ import annotations

import pytest

from vaultdiff.differ import SecretDiff
from vaultdiff.compactor import compact_diffs, CompactedPath, CompactReport


def _diff(
    path: str,
    changed=None,
    left_only=None,
    right_only=None,
) -> SecretDiff:
    return SecretDiff(
        path=path,
        changed_keys={k: ("old", "new") for k in (changed or [])},
        only_in_left={k: "v" for k in (left_only or [])},
        only_in_right={k: "v" for k in (right_only or [])},
    )


def test_compact_empty_list_returns_empty_report():
    report = compact_diffs([])
    assert report.total_paths == 0
    assert report.dirty_paths == 0
    assert report.paths == []


def test_compact_single_clean_diff():
    report = compact_diffs([_diff("secret/app")])
    assert report.total_paths == 1
    assert report.dirty_paths == 0
    entry = report.paths[0]
    assert entry.path == "secret/app"
    assert entry.occurrence_count == 1
    assert not entry.has_differences


def test_compact_single_dirty_diff():
    report = compact_diffs([_diff("secret/app", changed=["DB_PASS"])])
    assert report.dirty_paths == 1
    entry = report.paths[0]
    assert "DB_PASS" in entry.changed_keys
    assert entry.has_differences


def test_compact_merges_duplicate_paths():
    diffs = [
        _diff("secret/app", changed=["KEY_A"]),
        _diff("secret/app", changed=["KEY_B"]),
    ]
    report = compact_diffs(diffs)
    assert report.total_paths == 1
    entry = report.paths[0]
    assert entry.occurrence_count == 2
    assert set(entry.changed_keys) == {"KEY_A", "KEY_B"}


def test_compact_unions_left_and_right_only_keys():
    diffs = [
        _diff("secret/db", left_only=["OLD_HOST"]),
        _diff("secret/db", right_only=["NEW_HOST"]),
    ]
    report = compact_diffs(diffs)
    assert report.total_paths == 1
    entry = report.paths[0]
    assert "OLD_HOST" in entry.only_in_left
    assert "NEW_HOST" in entry.only_in_right
    assert entry.occurrence_count == 2


def test_compact_preserves_distinct_paths():
    diffs = [
        _diff("secret/a", changed=["X"]),
        _diff("secret/b", changed=["Y"]),
    ]
    report = compact_diffs(diffs)
    assert report.total_paths == 2
    paths = {p.path for p in report.paths}
    assert paths == {"secret/a", "secret/b"}


def test_compact_to_dict_structure():
    report = compact_diffs([_diff("secret/cfg", changed=["API_KEY"])])
    d = report.to_dict()
    assert "total_paths" in d
    assert "dirty_paths" in d
    assert "paths" in d
    assert d["paths"][0]["path"] == "secret/cfg"
    assert d["paths"][0]["has_differences"] is True


def test_compact_path_to_dict_sorted_keys():
    entry = CompactedPath(
        path="secret/x",
        changed_keys=["Z", "A", "M"],
        only_in_left=[],
        only_in_right=[],
        occurrence_count=1,
    )
    d = entry.to_dict()
    assert d["changed_keys"] == ["A", "M", "Z"]
