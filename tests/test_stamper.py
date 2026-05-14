"""Tests for vaultdiff.stamper."""
from __future__ import annotations

import datetime

import pytest

from vaultdiff.differ import SecretDiff
from vaultdiff.stamper import StampedDiff, StampReport, stamp_diffs

_TS = datetime.datetime(2024, 6, 1, 12, 0, 0, tzinfo=datetime.timezone.utc)


def _diff(path: str = "secret/a", changed=(), left=(), right=()) -> SecretDiff:
    return SecretDiff(
        path=path,
        changed_keys=set(changed),
        only_in_left=set(left),
        only_in_right=set(right),
    )


def test_stamp_empty_list_returns_empty_report():
    report = stamp_diffs([], at=_TS)
    assert report.total_paths == 0
    assert report.dirty_paths == 0
    assert report.entries == []


def test_stamp_clean_diff_has_no_differences():
    report = stamp_diffs([_diff()], at=_TS)
    assert report.total_paths == 1
    assert report.dirty_paths == 0
    assert not report.entries[0].has_differences()


def test_stamp_dirty_diff_counted():
    report = stamp_diffs([_diff(changed=("key",))], at=_TS)
    assert report.dirty_paths == 1


def test_stamp_assigns_timestamp():
    report = stamp_diffs([_diff()], at=_TS)
    assert report.entries[0].stamped_at == _TS


def test_stamp_assigns_label():
    report = stamp_diffs([_diff()], label="ci-run", at=_TS)
    assert report.entries[0].label == "ci-run"


def test_stamp_label_none_by_default():
    report = stamp_diffs([_diff()], at=_TS)
    assert report.entries[0].label is None


def test_stamped_diff_to_dict_keys():
    entry = StampedDiff(path="secret/x", diff=_diff("secret/x", changed=("k",)), stamped_at=_TS)
    d = entry.to_dict()
    assert d["path"] == "secret/x"
    assert d["has_differences"] is True
    assert d["changed_keys"] == ["k"]
    assert d["stamped_at"] == _TS.isoformat()
    assert d["label"] is None


def test_stamp_report_to_dict_structure():
    report = stamp_diffs([_diff("a"), _diff("b", left=("x",))], at=_TS)
    d = report.to_dict()
    assert d["total_paths"] == 2
    assert d["dirty_paths"] == 1
    assert len(d["entries"]) == 2


def test_stamp_multiple_diffs_all_present():
    diffs = [_diff(f"secret/{i}") for i in range(5)]
    report = stamp_diffs(diffs, at=_TS)
    assert report.total_paths == 5
    paths = [e.path for e in report.entries]
    assert "secret/3" in paths


def test_stamp_uses_current_time_when_at_not_given():
    before = datetime.datetime.now(datetime.timezone.utc)
    report = stamp_diffs([_diff()])
    after = datetime.datetime.now(datetime.timezone.utc)
    ts = report.entries[0].stamped_at
    assert before <= ts <= after
