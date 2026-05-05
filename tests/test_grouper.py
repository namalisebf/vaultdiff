"""Tests for vaultdiff.grouper."""

from __future__ import annotations

import pytest

from vaultdiff.differ import SecretDiff
from vaultdiff.grouper import GroupConfig, GroupRule, PathGroup, group_diffs


def _make_diff(path: str, changed: int = 0, left: int = 0, right: int = 0) -> SecretDiff:
    return SecretDiff(
        path=path,
        changed_keys={f"k{i}": ("a", "b") for i in range(changed)},
        only_in_left={f"l{i}": "v" for i in range(left)},
        only_in_right={f"r{i}": "v" for i in range(right)},
    )


def test_group_diffs_no_rules_all_go_to_default():
    diffs = [_make_diff("secret/app/db"), _make_diff("secret/app/api")]
    result = group_diffs(diffs)
    assert "other" in result
    assert len(result["other"].paths) == 2


def test_group_diffs_single_rule_matches():
    config = GroupConfig(rules=[GroupRule(name="app", pattern="secret/app/*")])
    diffs = [_make_diff("secret/app/db"), _make_diff("secret/infra/cache")]
    result = group_diffs(diffs, config)
    assert "app" in result
    assert "secret/app/db" in result["app"].paths
    assert "other" in result
    assert "secret/infra/cache" in result["other"].paths


def test_group_diffs_first_matching_rule_wins():
    config = GroupConfig(
        rules=[
            GroupRule(name="app", pattern="secret/app/*"),
            GroupRule(name="everything", pattern="secret/**"),
        ]
    )
    diffs = [_make_diff("secret/app/db")]
    result = group_diffs(diffs, config)
    assert "app" in result
    assert "everything" not in result


def test_group_diffs_custom_default_group():
    config = GroupConfig(default_group="ungrouped")
    diffs = [_make_diff("secret/misc/token")]
    result = group_diffs(diffs, config)
    assert "ungrouped" in result
    assert "other" not in result


def test_path_group_total_differences():
    diff = _make_diff("secret/app/db", changed=2, left=1, right=0)
    group = PathGroup(name="app", paths=["secret/app/db"], diffs=[diff])
    assert group.total_differences == 3


def test_path_group_total_differences_no_diffs():
    diff = _make_diff("secret/app/clean")
    group = PathGroup(name="app", paths=["secret/app/clean"], diffs=[diff])
    assert group.total_differences == 0


def test_path_group_to_dict():
    diff = _make_diff("secret/app/db", changed=1)
    group = PathGroup(name="app", paths=["secret/app/db"], diffs=[diff])
    d = group.to_dict()
    assert d["name"] == "app"
    assert d["path_count"] == 1
    assert d["total_differences"] == 1
    assert "secret/app/db" in d["paths"]


def test_group_config_from_dict():
    data = {
        "default_group": "misc",
        "rules": [
            {"name": "infra", "pattern": "secret/infra/*"},
            {"name": "app", "pattern": "secret/app/*"},
        ],
    }
    config = GroupConfig.from_dict(data)
    assert config.default_group == "misc"
    assert len(config.rules) == 2
    assert config.rules[0].name == "infra"
    assert config.rules[1].pattern == "secret/app/*"


def test_group_config_from_dict_empty():
    config = GroupConfig.from_dict({})
    assert config.default_group == "other"
    assert config.rules == []


def test_group_rule_matches_glob():
    rule = GroupRule(name="db", pattern="secret/*/db")
    assert rule.matches("secret/prod/db")
    assert not rule.matches("secret/prod/api")
