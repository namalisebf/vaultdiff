"""Tests for vaultdiff.zipper."""
from __future__ import annotations

import pytest

from vaultdiff.differ import SecretDiff
from vaultdiff.zipper import ZipReport, ZippedPath, zip_diffs


def _diff(
    path: str,
    changed: frozenset | None = None,
    only_left: frozenset | None = None,
    only_right: frozenset | None = None,
) -> SecretDiff:
    return SecretDiff(
        path=path,
        changed_keys=changed or frozenset(),
        only_in_left=only_left or frozenset(),
        only_in_right=only_right or frozenset(),
    )


def test_zip_empty_inputs_returns_empty_report():
    report = zip_diffs([], [])
    assert report.total_paths == 0
    assert report.matched_paths == 0
    assert report.unmatched_paths == 0


def test_zip_matching_paths_paired_correctly():
    left = [_diff("secret/app", changed=frozenset({"KEY"}))]
    right = [_diff("secret/app")]
    report = zip_diffs(left, right)
    assert report.total_paths == 1
    assert report.matched_paths == 1
    assert report.unmatched_paths == 0
    entry = report.entries[0]
    assert entry.in_both
    assert not entry.only_in_left
    assert not entry.only_in_right


def test_zip_path_only_in_left():
    left = [_diff("secret/only-left")]
    right = []
    report = zip_diffs(left, right)
    assert report.total_paths == 1
    assert report.unmatched_paths == 1
    entry = report.entries[0]
    assert entry.only_in_left
    assert entry.right_diff is None


def test_zip_path_only_in_right():
    left = []
    right = [_diff("secret/only-right")]
    report = zip_diffs(left, right)
    assert report.total_paths == 1
    assert report.unmatched_paths == 1
    entry = report.entries[0]
    assert entry.only_in_right
    assert entry.left_diff is None


def test_zip_entries_sorted_by_path():
    left = [_diff("z/path"), _diff("a/path")]
    right = [_diff("m/path")]
    report = zip_diffs(left, right)
    paths = [e.path for e in report.entries]
    assert paths == sorted(paths)


def test_zipped_path_to_dict_structure():
    diff = _diff("secret/app", changed=frozenset({"DB_PASS"}))
    entry = ZippedPath(path="secret/app", left_diff=diff, right_diff=None)
    d = entry.to_dict()
    assert d["path"] == "secret/app"
    assert d["only_in_left"] is True
    assert d["in_both"] is False
    assert d["left_diff"]["changed_keys"] == ["DB_PASS"]
    assert d["right_diff"] is None


def test_zip_report_to_dict_keys():
    report = zip_diffs(
        [_diff("secret/a")],
        [_diff("secret/a"), _diff("secret/b")],
    )
    d = report.to_dict()
    assert "total_paths" in d
    assert "matched_paths" in d
    assert "unmatched_paths" in d
    assert "entries" in d
    assert d["total_paths"] == 2
    assert d["matched_paths"] == 1
    assert d["unmatched_paths"] == 1
