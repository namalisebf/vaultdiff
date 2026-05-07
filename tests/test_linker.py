"""Tests for vaultdiff.linker."""
from __future__ import annotations

import pytest

from vaultdiff.differ import SecretDiff
from vaultdiff.linker import LinkedKey, LinkReport, build_link_report


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _diff(
    path: str,
    changed: list | None = None,
    only_in_left: list | None = None,
    only_in_right: list | None = None,
) -> SecretDiff:
    from vaultdiff.differ import DiffEntry

    entries = []
    for key, left, right in (changed or []):
        entries.append(DiffEntry(key=key, left_value=left, right_value=right))

    return SecretDiff(
        path=path,
        changed=entries,
        only_in_left=only_in_left or [],
        only_in_right=only_in_right or [],
    )


# ---------------------------------------------------------------------------
# LinkedKey
# ---------------------------------------------------------------------------

def test_linked_key_link_count():
    lk = LinkedKey(key="DB_PASS", paths=["a", "b", "c"])
    assert lk.link_count == 3


def test_linked_key_to_dict():
    lk = LinkedKey(key="API_KEY", paths=["x", "y"])
    d = lk.to_dict()
    assert d["key"] == "API_KEY"
    assert d["link_count"] == 2
    assert d["paths"] == ["x", "y"]


# ---------------------------------------------------------------------------
# LinkReport
# ---------------------------------------------------------------------------

def test_link_report_totals():
    report = LinkReport(
        linked_keys=[
            LinkedKey(key="A", paths=["p1", "p2"]),
            LinkedKey(key="B", paths=["p2", "p3"]),
        ]
    )
    assert report.total_shared_keys == 2
    assert report.total_affected_paths == 3


def test_link_report_to_dict_structure():
    report = LinkReport(linked_keys=[LinkedKey(key="X", paths=["a", "b"])])
    d = report.to_dict()
    assert "total_shared_keys" in d
    assert "total_affected_paths" in d
    assert isinstance(d["linked_keys"], list)


# ---------------------------------------------------------------------------
# build_link_report
# ---------------------------------------------------------------------------

def test_build_link_report_empty_diffs():
    report = build_link_report([])
    assert report.total_shared_keys == 0
    assert report.total_affected_paths == 0


def test_build_link_report_no_shared_keys():
    diffs = [
        _diff("secret/a", changed=[("KEY_A", "old", "new")]),
        _diff("secret/b", changed=[("KEY_B", "old", "new")]),
    ]
    report = build_link_report(diffs)
    assert report.total_shared_keys == 0


def test_build_link_report_detects_shared_changed_key():
    diffs = [
        _diff("secret/a", changed=[("DB_PASS", "old", "new")]),
        _diff("secret/b", changed=[("DB_PASS", "x", "y")]),
    ]
    report = build_link_report(diffs)
    assert report.total_shared_keys == 1
    assert report.linked_keys[0].key == "DB_PASS"
    assert set(report.linked_keys[0].paths) == {"secret/a", "secret/b"}


def test_build_link_report_detects_shared_only_in_left():
    diffs = [
        _diff("secret/a", only_in_left=["REMOVED_KEY"]),
        _diff("secret/b", only_in_left=["REMOVED_KEY"]),
    ]
    report = build_link_report(diffs)
    assert report.total_shared_keys == 1


def test_build_link_report_detects_shared_only_in_right():
    diffs = [
        _diff("secret/a", only_in_right=["NEW_KEY"]),
        _diff("secret/b", only_in_right=["NEW_KEY"]),
        _diff("secret/c", only_in_right=["NEW_KEY"]),
    ]
    report = build_link_report(diffs)
    assert report.total_shared_keys == 1
    assert report.linked_keys[0].link_count == 3


def test_build_link_report_respects_min_links():
    diffs = [
        _diff("secret/a", changed=[("SHARED", "1", "2")]),
        _diff("secret/b", changed=[("SHARED", "3", "4")]),
        _diff("secret/c", changed=[("UNIQUE", "a", "b")]),
    ]
    report = build_link_report(diffs, min_links=3)
    assert report.total_shared_keys == 0

    report2 = build_link_report(diffs, min_links=2)
    assert report2.total_shared_keys == 1


def test_build_link_report_deduplicates_paths():
    # Same path appearing twice for same key should only be counted once.
    diffs = [
        _diff("secret/a", changed=[("K", "1", "2")], only_in_left=["K"]),
        _diff("secret/b", changed=[("K", "3", "4")]),
    ]
    report = build_link_report(diffs)
    lk = report.linked_keys[0]
    assert lk.paths.count("secret/a") == 1
