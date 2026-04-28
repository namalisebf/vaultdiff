"""Tests for vaultdiff.summarizer."""

import pytest
from vaultdiff.differ import SecretDiff
from vaultdiff.summarizer import SummaryStats, summarize, format_summary_text


def _diff(
    path="secret/app",
    changed=None,
    only_in_left=None,
    only_in_right=None,
) -> SecretDiff:
    return SecretDiff(
        path=path,
        changed=changed or {},
        only_in_left=only_in_left or {},
        only_in_right=only_in_right or {},
    )


def test_summarize_empty_list():
    stats = summarize([])
    assert stats.total_paths == 0
    assert stats.total_differences == 0
    assert stats.paths_with_differences == 0


def test_summarize_no_differences():
    diffs = [_diff("secret/a"), _diff("secret/b")]
    stats = summarize(diffs)
    assert stats.total_paths == 2
    assert stats.clean_paths == 2
    assert stats.paths_with_differences == 0
    assert stats.total_differences == 0


def test_summarize_counts_changed_keys():
    diffs = [
        _diff("secret/a", changed={"KEY": ("old", "new")}),
        _diff("secret/b", changed={"X": ("1", "2"), "Y": ("a", "b")}),
    ]
    stats = summarize(diffs)
    assert stats.total_changed_keys == 3
    assert stats.paths_with_differences == 2


def test_summarize_counts_added_keys():
    diffs = [_diff("secret/a", only_in_right={"NEW_KEY": "value"})]
    stats = summarize(diffs)
    assert stats.total_added_keys == 1
    assert stats.total_removed_keys == 0
    assert stats.paths_with_differences == 1


def test_summarize_counts_removed_keys():
    diffs = [_diff("secret/a", only_in_left={"OLD_KEY": "value"})]
    stats = summarize(diffs)
    assert stats.total_removed_keys == 1
    assert stats.total_added_keys == 0
    assert stats.paths_with_differences == 1


def test_summarize_mixed_diffs():
    diffs = [
        _diff("secret/a", changed={"K": ("v1", "v2")}),
        _diff("secret/b"),
        _diff("secret/c", only_in_left={"GONE": "x"}, only_in_right={"NEW": "y"}),
    ]
    stats = summarize(diffs)
    assert stats.total_paths == 3
    assert stats.clean_paths == 1
    assert stats.paths_with_differences == 2
    assert stats.total_changed_keys == 1
    assert stats.total_removed_keys == 1
    assert stats.total_added_keys == 1


def test_summarize_to_dict_keys():
    stats = summarize([_diff("secret/a", changed={"K": ("a", "b")})])
    d = stats.to_dict()
    assert "total_paths" in d
    assert "paths_with_differences" in d
    assert "total_differences" in d
    assert d["total_changed_keys"] == 1


def test_format_summary_text_contains_counts():
    diffs = [_diff("secret/a", changed={"K": ("a", "b")})]
    stats = summarize(diffs)
    text = format_summary_text(stats)
    assert "Paths scanned" in text
    assert "1" in text
    assert "Changed keys" in text


def test_format_summary_text_shows_only_in_left():
    diffs = [_diff("secret/left-only", only_in_left={"X": "1"})]
    stats = summarize(diffs)
    # Manually mark as only_in_left path for coverage of that branch
    # (only_in_left path detection requires no changed/only_in_right)
    text = format_summary_text(stats)
    assert "Removed keys" in text
