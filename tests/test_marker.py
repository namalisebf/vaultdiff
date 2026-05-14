"""Tests for vaultdiff.marker."""
from __future__ import annotations

import pytest

from vaultdiff.differ import SecretDiff
from vaultdiff.marker import MarkConfig, MarkRule, MarkedPath, mark_diffs


def _diff(path: str, changed=(), left=(), right=()) -> SecretDiff:
    return SecretDiff(
        path=path,
        changed_keys=set(changed),
        only_in_left=set(left),
        only_in_right=set(right),
    )


def test_mark_empty_list_returns_empty_report():
    report = mark_diffs([])
    assert report.total_paths() == 0
    assert report.dirty_paths() == 0
    assert report.entries == []


def test_mark_no_rules_uses_default_mark():
    config = MarkConfig(default_mark="unclassified")
    report = mark_diffs([_diff("secret/a")], config)
    assert len(report.entries) == 1
    assert report.entries[0].mark == "unclassified"


def test_mark_glob_rule_matches():
    config = MarkConfig(rules=[MarkRule(pattern="prod/*", mark="production")])
    report = mark_diffs([_diff("prod/db"), _diff("dev/db")], config)
    marks = {e.path: e.mark for e in report.entries}
    assert marks["prod/db"] == "production"
    assert marks["dev/db"] == ""


def test_mark_prefix_rule_matches():
    config = MarkConfig(
        rules=[MarkRule(pattern="staging/", mark="staging", mode="prefix")]
    )
    report = mark_diffs([_diff("staging/api"), _diff("prod/api")], config)
    marks = {e.path: e.mark for e in report.entries}
    assert marks["staging/api"] == "staging"
    assert marks["prod/api"] == ""


def test_mark_regex_rule_matches():
    config = MarkConfig(
        rules=[MarkRule(pattern=r"^secret/v\d+/", mark="versioned", mode="regex")]
    )
    report = mark_diffs([_diff("secret/v2/key"), _diff("secret/other")], config)
    marks = {e.path: e.mark for e in report.entries}
    assert marks["secret/v2/key"] == "versioned"
    assert marks["secret/other"] == ""


def test_first_matching_rule_wins():
    config = MarkConfig(
        rules=[
            MarkRule(pattern="prod/*", mark="first"),
            MarkRule(pattern="prod/*", mark="second"),
        ]
    )
    report = mark_diffs([_diff("prod/x")], config)
    assert report.entries[0].mark == "first"


def test_mark_config_from_dict():
    data = {
        "rules": [{"pattern": "prod/*", "mark": "production", "mode": "glob"}],
        "default_mark": "other",
    }
    config = MarkConfig.from_dict(data)
    assert len(config.rules) == 1
    assert config.rules[0].mark == "production"
    assert config.default_mark == "other"


def test_mark_config_from_dict_empty():
    config = MarkConfig.from_dict({})
    assert config.rules == []
    assert config.default_mark == ""


def test_marked_path_has_differences_true():
    diff = _diff("secret/x", changed=("key",))
    entry = MarkedPath(path="secret/x", mark="prod", diff=diff)
    assert entry.has_differences() is True


def test_marked_path_has_differences_false():
    diff = _diff("secret/x")
    entry = MarkedPath(path="secret/x", mark="prod", diff=diff)
    assert entry.has_differences() is False


def test_to_dict_structure():
    diff = _diff("secret/x", changed=("k",))
    entry = MarkedPath(path="secret/x", mark="critical", diff=diff)
    d = entry.to_dict()
    assert d["path"] == "secret/x"
    assert d["mark"] == "critical"
    assert d["has_differences"] is True
    assert "k" in d["changed_keys"]


def test_report_to_dict_keys():
    diffs = [_diff("a", changed=("x",)), _diff("b")]
    report = mark_diffs(diffs)
    d = report.to_dict()
    assert d["total_paths"] == 2
    assert d["dirty_paths"] == 1
    assert len(d["entries"]) == 2
