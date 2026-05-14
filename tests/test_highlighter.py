"""Tests for vaultdiff.highlighter."""
from __future__ import annotations

import pytest

from vaultdiff.differ import SecretDiff
from vaultdiff.highlighter import HighlightedPath, HighlightReport, highlight_diffs


def _diff(
    path: str = "secret/app",
    changed=None,
    only_left=None,
    only_right=None,
) -> SecretDiff:
    """Build a minimal SecretDiff for testing."""
    from vaultdiff.differ import KeyDiff

    changed_keys = [
        KeyDiff(key=k, left_value="old", right_value="new") for k in (changed or [])
    ]
    return SecretDiff(
        path=path,
        changed_keys=changed_keys,
        only_in_left=dict.fromkeys(only_left or []),
        only_in_right=dict.fromkeys(only_right or []),
    )


def test_highlight_empty_list_returns_empty_report():
    report = highlight_diffs([])
    assert report.total_paths == 0
    assert report.highlighted_paths == 0
    assert report.entries == []


def test_highlight_clean_diff_has_no_highlights():
    report = highlight_diffs([_diff("secret/clean")])
    assert report.total_paths == 1
    assert report.highlighted_paths == 0
    entry = report.entries[0]
    assert not entry.has_highlights


def test_highlight_detects_changed_keys():
    report = highlight_diffs([_diff(changed=["api_key", "token"])])
    entry = report.entries[0]
    assert entry.changed_keys == {"api_key", "token"}
    assert entry.has_highlights


def test_highlight_detects_added_keys():
    report = highlight_diffs([_diff(only_right=["new_key"])])
    entry = report.entries[0]
    assert entry.added_keys == {"new_key"}
    assert entry.has_highlights


def test_highlight_detects_removed_keys():
    report = highlight_diffs([_diff(only_left=["old_key"])])
    entry = report.entries[0]
    assert entry.removed_keys == {"old_key"}
    assert entry.has_highlights


def test_highlight_report_counts_correctly():
    diffs = [
        _diff("secret/a", changed=["x"]),
        _diff("secret/b"),
        _diff("secret/c", only_right=["y"]),
    ]
    report = highlight_diffs(diffs)
    assert report.total_paths == 3
    assert report.highlighted_paths == 2


def test_highlighted_path_to_dict_keys():
    report = highlight_diffs([_diff(changed=["k1"], only_left=["k2"], only_right=["k3"])])
    d = report.entries[0].to_dict()
    assert set(d.keys()) == {"path", "changed_keys", "added_keys", "removed_keys", "has_highlights"}
    assert d["has_highlights"] is True


def test_highlight_report_to_dict_structure():
    report = highlight_diffs([_diff()])
    d = report.to_dict()
    assert "total_paths" in d
    assert "highlighted_paths" in d
    assert "entries" in d
    assert isinstance(d["entries"], list)
