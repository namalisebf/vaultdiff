"""Tests for vaultdiff.baseline module."""

import json
import os
import pytest

from vaultdiff.baseline import (
    BaselineEntry,
    compare_to_baseline,
    load_baseline,
    save_baseline,
)
from vaultdiff.differ import SecretDiff


def _make_diff(
    changed=None,
    only_in_left=None,
    only_in_right=None,
) -> SecretDiff:
    return SecretDiff(
        changed_keys=changed or {},
        only_in_left=only_in_left or [],
        only_in_right=only_in_right or [],
    )


def test_baseline_entry_from_diff():
    diff = _make_diff(
        changed={"KEY": ("a", "b")},
        only_in_left=["OLD"],
        only_in_right=["NEW"],
    )
    entry = BaselineEntry.from_diff("secret/app", diff)
    assert entry.path == "secret/app"
    assert entry.changed_keys == ["KEY"]
    assert entry.only_in_left == ["OLD"]
    assert entry.only_in_right == ["NEW"]


def test_save_and_load_baseline(tmp_path):
    baseline_file = str(tmp_path / "baseline.json")
    entries = [
        BaselineEntry("secret/a", ["X"], [], ["Y"]),
        BaselineEntry("secret/b", [], ["Z"], []),
    ]
    save_baseline(baseline_file, entries)
    assert os.path.exists(baseline_file)

    loaded = load_baseline(baseline_file)
    assert len(loaded) == 2
    assert loaded[0].path == "secret/a"
    assert loaded[0].changed_keys == ["X"]
    assert loaded[1].only_in_left == ["Z"]


def test_load_baseline_missing_file():
    with pytest.raises(FileNotFoundError, match="Baseline file not found"):
        load_baseline("/nonexistent/baseline.json")


def test_compare_no_regressions():
    baseline = [BaselineEntry("secret/app", ["KEY"], [], [])]
    current = {"secret/app": _make_diff(changed={"KEY": ("old", "new")})}
    result = compare_to_baseline(current, baseline)
    assert result == {}


def test_compare_detects_new_changed_key():
    baseline = [BaselineEntry("secret/app", ["KEY"], [], [])]
    current = {
        "secret/app": _make_diff(changed={"KEY": ("a", "b"), "NEW_KEY": ("x", "y")})
    }
    result = compare_to_baseline(current, baseline)
    assert "secret/app" in result
    assert any("NEW_KEY" in msg for msg in result["secret/app"])


def test_compare_detects_path_not_in_baseline():
    baseline: list = []
    current = {"secret/new": _make_diff(changed={"A": ("1", "2")})}
    result = compare_to_baseline(current, baseline)
    assert "secret/new" in result
    assert result["secret/new"] == ["path not in baseline"]


def test_compare_ignores_resolved_issues():
    baseline = [BaselineEntry("secret/app", ["OLD"], ["L"], ["R"])]
    current = {"secret/app": _make_diff()}
    result = compare_to_baseline(current, baseline)
    assert result == {}


def test_save_baseline_json_structure(tmp_path):
    baseline_file = str(tmp_path / "b.json")
    entries = [BaselineEntry("secret/x", ["K"], [], [])]
    save_baseline(baseline_file, entries)
    with open(baseline_file) as fh:
        data = json.load(fh)
    assert isinstance(data, list)
    assert data[0]["path"] == "secret/x"
    assert data[0]["changed_keys"] == ["K"]
