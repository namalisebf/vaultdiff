"""Tests for vaultdiff.aggregator."""

from unittest.mock import MagicMock

import pytest

from vaultdiff.aggregator import AggregatedPath, AggregateReport, aggregate_diffs
from vaultdiff.differ import SecretDiff


def _make_diff(
    changed=None, only_in_left=None, only_in_right=None
) -> SecretDiff:
    diff = MagicMock(spec=SecretDiff)
    diff.changed = changed or {}
    diff.only_in_left = only_in_left or {}
    diff.only_in_right = only_in_right or {}
    return diff


def test_aggregate_empty_input():
    report = aggregate_diffs({})
    assert report.paths == []
    assert report.dirty_paths == []
    assert report.clean_paths == []


def test_aggregate_single_env_no_differences():
    env_diffs = {"prod": {"secret/app": _make_diff()}}
    report = aggregate_diffs(env_diffs)
    assert len(report.paths) == 1
    assert report.paths[0].path == "secret/app"
    assert not report.paths[0].has_differences()
    assert len(report.clean_paths) == 1
    assert len(report.dirty_paths) == 0


def test_aggregate_single_env_with_differences():
    diff = _make_diff(changed={"KEY": ("a", "b")}, only_in_left={"OLD": "v"})
    env_diffs = {"prod": {"secret/app": diff}}
    report = aggregate_diffs(env_diffs)
    agg = report.paths[0]
    assert agg.total_changed == 1
    assert agg.total_only_in_left == 1
    assert agg.total_only_in_right == 0
    assert agg.has_differences()


def test_aggregate_multiple_envs_same_path():
    diff_prod = _make_diff(changed={"A": ("1", "2")})
    diff_staging = _make_diff(only_in_right={"B": "v"})
    env_diffs = {
        "prod": {"secret/app": diff_prod},
        "staging": {"secret/app": diff_staging},
    }
    report = aggregate_diffs(env_diffs)
    assert len(report.paths) == 1
    agg = report.paths[0]
    assert agg.total_changed == 1
    assert agg.total_only_in_right == 1
    assert set(agg.environments) == {"prod", "staging"}


def test_aggregate_multiple_paths():
    env_diffs = {
        "prod": {
            "secret/a": _make_diff(changed={"X": ("1", "2")}),
            "secret/b": _make_diff(),
        }
    }
    report = aggregate_diffs(env_diffs)
    assert len(report.paths) == 2
    paths_by_name = {p.path: p for p in report.paths}
    assert paths_by_name["secret/a"].has_differences()
    assert not paths_by_name["secret/b"].has_differences()


def test_aggregate_environments_ordered():
    env_diffs = {
        "z_env": {"secret/x": _make_diff()},
        "a_env": {"secret/x": _make_diff()},
    }
    report = aggregate_diffs(env_diffs, environments=["a_env", "z_env"])
    assert report.environments == ["a_env", "z_env"]


def test_aggregate_to_dict_structure():
    diff = _make_diff(changed={"K": ("old", "new")})
    env_diffs = {"prod": {"secret/cfg": diff}}
    report = aggregate_diffs(env_diffs)
    d = report.to_dict()
    assert d["total_paths"] == 1
    assert d["dirty_paths"] == 1
    assert d["clean_paths"] == 0
    assert d["paths"][0]["path"] == "secret/cfg"
    assert d["paths"][0]["has_differences"] is True


def test_aggregated_path_details_keyed_by_env():
    diff_prod = _make_diff(changed={"X": ("a", "b")})
    env_diffs = {"prod": {"secret/svc": diff_prod}}
    report = aggregate_diffs(env_diffs)
    agg = report.paths[0]
    assert "prod" in agg.details
    assert agg.details["prod"] is diff_prod
