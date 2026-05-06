"""Tests for vaultdiff.deduplicator."""
import pytest

from vaultdiff.deduplicator import (
    DeduplicationReport,
    DuplicateGroup,
    deduplicate,
    _hash_value,
)
from vaultdiff.differ import SecretDiff


def _diff(path: str, left: dict, right: dict | None = None) -> SecretDiff:
    right = right or {}
    return SecretDiff(
        path=path,
        left=left,
        right=right,
        changed_keys=[],
        only_in_left=[],
        only_in_right=[],
    )


# ---------------------------------------------------------------------------
# DuplicateGroup helpers
# ---------------------------------------------------------------------------

def test_duplicate_group_count():
    g = DuplicateGroup(key="db_pass", value="secret", paths=["a", "b", "c"])
    assert g.count == 3


def test_duplicate_group_to_dict_hides_value():
    g = DuplicateGroup(key="api_key", value="plaintext", paths=["p1", "p2"])
    d = g.to_dict()
    assert d["key"] == "api_key"
    assert "plaintext" not in str(d)
    assert len(d["value_hash"]) == 12
    assert d["count"] == 2
    assert d["paths"] == ["p1", "p2"]


# ---------------------------------------------------------------------------
# deduplicate — basic cases
# ---------------------------------------------------------------------------

def test_deduplicate_empty_list():
    report = deduplicate([])
    assert report.groups == []
    assert report.total_duplicates == 0


def test_deduplicate_no_shared_values():
    diffs = [
        _diff("env/prod", {"key": "alpha"}),
        _diff("env/staging", {"key": "beta"}),
    ]
    report = deduplicate(diffs)
    assert report.groups == []


def test_deduplicate_detects_shared_value():
    diffs = [
        _diff("env/prod", {"db_pass": "shared_secret"}),
        _diff("env/staging", {"db_pass": "shared_secret"}),
    ]
    report = deduplicate(diffs)
    assert len(report.groups) == 1
    g = report.groups[0]
    assert g.key == "db_pass"
    assert set(g.paths) == {"env/prod", "env/staging"}


def test_deduplicate_right_side():
    diffs = [
        _diff("a", left={"k": "x"}, right={"k": "same"}),
        _diff("b", left={"k": "y"}, right={"k": "same"}),
    ]
    report_left = deduplicate(diffs, side="left")
    report_right = deduplicate(diffs, side="right")
    assert report_left.groups == []
    assert len(report_right.groups) == 1


def test_deduplicate_min_count_filters():
    diffs = [
        _diff("a", {"k": "v"}),
        _diff("b", {"k": "v"}),
        _diff("c", {"k": "v"}),
    ]
    report2 = deduplicate(diffs, min_count=2)
    report4 = deduplicate(diffs, min_count=4)
    assert len(report2.groups) == 1
    assert report4.groups == []


def test_deduplicate_invalid_side_raises():
    with pytest.raises(ValueError, match="side must be"):
        deduplicate([], side="both")


def test_deduplication_report_to_dict():
    diffs = [
        _diff("x", {"pw": "abc"}),
        _diff("y", {"pw": "abc"}),
    ]
    report = deduplicate(diffs)
    d = report.to_dict()
    assert d["total_duplicates"] == 2
    assert d["unique_keys_with_duplicates"] == 1
    assert len(d["groups"]) == 1


def test_hash_value_is_deterministic():
    assert _hash_value("hello") == _hash_value("hello")
    assert _hash_value("hello") != _hash_value("world")
