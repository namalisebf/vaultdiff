"""Tests for vaultdiff.joiner."""
from __future__ import annotations

import pytest

from vaultdiff.differ import SecretDiff
from vaultdiff.joiner import JoinReport, JoinedPath, join_diffs


def _diff(path: str, changed=(), only_left=(), only_right=()) -> SecretDiff:
    return SecretDiff(
        path=path,
        changed=dict.fromkeys(changed, ("old", "new")),
        only_in_left=dict.fromkeys(only_left, "v"),
        only_in_right=dict.fromkeys(only_right, "v"),
    )


def test_join_empty_input_returns_empty_report():
    report = join_diffs({})
    assert report.total_paths == 0
    assert report.dirty_paths == 0
    assert report.joined == []


def test_join_single_label_single_path():
    report = join_diffs({"prod": [_diff("secret/app")]})
    assert report.total_paths == 1
    joined = report.joined[0]
    assert joined.path == "secret/app"
    assert "prod" in joined.labels()


def test_join_two_labels_same_path_merged():
    report = join_diffs({
        "prod": [_diff("secret/app", changed=["key1"])],
        "staging": [_diff("secret/app")],
    })
    assert report.total_paths == 1
    joined = report.joined[0]
    assert set(joined.labels()) == {"prod", "staging"}


def test_join_two_labels_different_paths():
    report = join_diffs({
        "prod": [_diff("secret/a")],
        "staging": [_diff("secret/b")],
    })
    assert report.total_paths == 2
    paths = {j.path for j in report.joined}
    assert paths == {"secret/a", "secret/b"}


def test_has_differences_false_when_all_clean():
    report = join_diffs({"prod": [_diff("secret/app")]})
    assert not report.joined[0].has_differences()
    assert report.dirty_paths == 0


def test_has_differences_true_when_any_label_has_diff():
    report = join_diffs({
        "prod": [_diff("secret/app", changed=["password"])],
        "staging": [_diff("secret/app")],
    })
    assert report.joined[0].has_differences()
    assert report.dirty_paths == 1


def test_to_dict_structure():
    report = join_diffs({"prod": [_diff("secret/app", changed=["k"])]})
    d = report.to_dict()
    assert d["total_paths"] == 1
    assert d["dirty_paths"] == 1
    entry = d["joined"][0]
    assert entry["path"] == "secret/app"
    assert entry["has_differences"] is True
    assert "prod" in entry["entries"]
    assert "k" in entry["entries"]["prod"]["changed"]


def test_joined_path_only_in_left_recorded():
    report = join_diffs({"env": [_diff("secret/x", only_left=["gone"])]})
    d = report.to_dict()
    assert "gone" in d["joined"][0]["entries"]["env"]["only_in_left"]


def test_joined_path_only_in_right_recorded():
    report = join_diffs({"env": [_diff("secret/x", only_right=["new_key"])]})
    d = report.to_dict()
    assert "new_key" in d["joined"][0]["entries"]["env"]["only_in_right"]
