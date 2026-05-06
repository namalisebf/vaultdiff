"""Unit tests for vaultdiff.tracer."""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from vaultdiff.differ import SecretDiff
from vaultdiff.tracer import (
    TracePoint,
    TraceReport,
    build_trace_report,
    trace_diffs,
)


def _make_diff(
    path: str = "secret/app",
    changed: dict | None = None,
    only_left: dict | None = None,
    only_right: dict | None = None,
) -> SecretDiff:
    return SecretDiff(
        path=path,
        changed_keys=changed or {},
        only_in_left=only_left or {},
        only_in_right=only_right or {},
    )


def test_trace_point_has_changes_false_when_clean():
    pt = TracePoint(label="prod", path="secret/app")
    assert pt.has_changes is False


def test_trace_point_has_changes_true_when_changed():
    pt = TracePoint(label="prod", path="secret/app", changed_keys=["KEY"])
    assert pt.has_changes is True


def test_trace_point_to_dict_keys():
    pt = TracePoint(label="staging", path="secret/db", only_in_right=["NEW_KEY"])
    d = pt.to_dict()
    assert d["label"] == "staging"
    assert d["path"] == "secret/db"
    assert d["has_changes"] is True
    assert d["only_in_right"] == ["NEW_KEY"]


def test_trace_diffs_returns_one_point_per_diff():
    diffs = [
        _make_diff("secret/a", changed={"X": ("old", "new")}),
        _make_diff("secret/b"),
    ]
    points = trace_diffs("prod", diffs)
    assert len(points) == 2
    assert points[0].label == "prod"
    assert points[0].path == "secret/a"
    assert "X" in points[0].changed_keys
    assert points[1].has_changes is False


def test_trace_diffs_empty_list_returns_empty():
    assert trace_diffs("dev", []) == []


def test_build_trace_report_aggregates_labels():
    labelled = {
        "prod": [_make_diff("secret/x", changed={"A": ("1", "2")})],
        "staging": [_make_diff("secret/x")],
    }
    report = build_trace_report(labelled)
    assert len(report.points) == 2
    assert report.total_changes == 1
    assert "secret/x" in report.paths_with_changes


def test_build_trace_report_empty_input():
    report = build_trace_report({})
    assert report.total_changes == 0
    assert report.paths_with_changes == []


def test_trace_report_to_dict_structure():
    labelled = {
        "prod": [
            _make_diff("secret/a", only_left={"GONE": "v"}),
        ]
    }
    report = build_trace_report(labelled)
    d = report.to_dict()
    assert "total_changes" in d
    assert "paths_with_changes" in d
    assert "points" in d
    assert d["total_changes"] == 1


def test_paths_with_changes_deduplicates_across_labels():
    labelled = {
        "prod": [_make_diff("secret/shared", changed={"K": ("a", "b")})],
        "staging": [_make_diff("secret/shared", changed={"K": ("a", "c")})],
    }
    report = build_trace_report(labelled)
    assert report.paths_with_changes == ["secret/shared"]
