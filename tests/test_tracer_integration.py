"""Integration tests for tracer: wiring trace_diffs + build_trace_report together."""
from __future__ import annotations

from vaultdiff.differ import SecretDiff
from vaultdiff.tracer import TracePoint, TraceReport, build_trace_report, trace_diffs


def _diff(
    path: str,
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


def test_all_clean_paths_produce_zero_total_changes():
    labelled = {
        "prod": [_diff("secret/a"), _diff("secret/b")],
        "staging": [_diff("secret/a"), _diff("secret/b")],
    }
    report = build_trace_report(labelled)
    assert report.total_changes == 0
    assert report.paths_with_changes == []


def test_single_label_multiple_paths_all_counted():
    labelled = {
        "prod": [
            _diff("secret/x", changed={"A": ("1", "2")}),
            _diff("secret/y", only_right={"NEW": "val"}),
        ]
    }
    report = build_trace_report(labelled)
    assert report.total_changes == 2
    assert sorted(report.paths_with_changes) == ["secret/x", "secret/y"]


def test_multiple_labels_same_path_accumulates_points():
    labelled = {
        "prod": [_diff("secret/shared", changed={"K": ("a", "b")})],
        "staging": [_diff("secret/shared", only_left={"OLD": "v"})],
        "dev": [_diff("secret/shared")],
    }
    report = build_trace_report(labelled)
    assert len(report.points) == 3
    assert report.total_changes == 2
    # paths_with_changes deduplicates
    assert report.paths_with_changes == ["secret/shared"]


def test_trace_point_is_dataclass_instance():
    diffs = [_diff("secret/z", only_right={"X": "1"})]
    points = trace_diffs("env", diffs)
    assert isinstance(points[0], TracePoint)
    assert points[0].only_in_right == ["X"]


def test_report_to_dict_roundtrip_contains_all_labels():
    labelled = {
        "prod": [_diff("secret/a", changed={"K": ("old", "new")})],
        "staging": [_diff("secret/b")],
    }
    report = build_trace_report(labelled)
    d = report.to_dict()
    labels_in_points = {p["label"] for p in d["points"]}
    assert labels_in_points == {"prod", "staging"}
