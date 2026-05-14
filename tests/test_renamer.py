"""Tests for vaultdiff.renamer."""
from __future__ import annotations

import pytest

from vaultdiff.differ import SecretDiff
from vaultdiff.renamer import (
    RenameConfig,
    RenameRule,
    RenamedDiff,
    rename_diffs,
)


def _diff(path: str) -> SecretDiff:
    return SecretDiff(
        path=path,
        changed_keys={},
        only_in_left=set(),
        only_in_right=set(),
    )


def test_rename_empty_list_returns_empty():
    config = RenameConfig()
    assert rename_diffs([], config) == []


def test_rename_no_rules_keeps_original_path():
    config = RenameConfig()
    results = rename_diffs([_diff("secret/prod/db")], config)
    assert len(results) == 1
    r = results[0]
    assert r.original_path == "secret/prod/db"
    assert r.renamed_path == "secret/prod/db"
    assert r.rule_applied is False


def test_rename_prefix_rule_rewrites_path():
    rule = RenameRule(pattern="secret/prod/", replacement="secret/staging/", mode="prefix")
    config = RenameConfig(rules=[rule])
    results = rename_diffs([_diff("secret/prod/db")], config)
    assert results[0].renamed_path == "secret/staging/db"
    assert results[0].rule_applied is True


def test_rename_prefix_rule_no_match_keeps_original():
    rule = RenameRule(pattern="secret/prod/", replacement="secret/staging/", mode="prefix")
    config = RenameConfig(rules=[rule])
    results = rename_diffs([_diff("secret/dev/db")], config)
    assert results[0].renamed_path == "secret/dev/db"
    assert results[0].rule_applied is False


def test_rename_regex_rule_rewrites_path():
    rule = RenameRule(pattern=r"prod", replacement="staging", mode="regex")
    config = RenameConfig(rules=[rule])
    results = rename_diffs([_diff("secret/prod/api")], config)
    assert results[0].renamed_path == "secret/staging/api"
    assert results[0].rule_applied is True


def test_first_matching_rule_wins():
    r1 = RenameRule(pattern="secret/", replacement="vault/", mode="prefix")
    r2 = RenameRule(pattern="secret/prod/", replacement="vault/staging/", mode="prefix")
    config = RenameConfig(rules=[r1, r2])
    results = rename_diffs([_diff("secret/prod/db")], config)
    assert results[0].renamed_path == "vault/prod/db"


def test_rename_config_from_dict():
    data = {
        "rules": [
            {"pattern": "secret/", "replacement": "kv/", "mode": "prefix"},
        ]
    }
    config = RenameConfig.from_dict(data)
    assert len(config.rules) == 1
    assert config.rules[0].pattern == "secret/"
    assert config.rules[0].mode == "prefix"


def test_rename_config_from_dict_empty():
    config = RenameConfig.from_dict({})
    assert config.rules == []


def test_renamed_diff_to_dict_keys():
    diff = _diff("secret/prod/db")
    rd = RenamedDiff(
        original_path="secret/prod/db",
        renamed_path="secret/staging/db",
        diff=diff,
        rule_applied=True,
    )
    d = rd.to_dict()
    assert "original_path" in d
    assert "renamed_path" in d
    assert "rule_applied" in d
    assert d["rule_applied"] is True


def test_rename_multiple_diffs_independent():
    rule = RenameRule(pattern="prod/", replacement="uat/", mode="prefix")
    config = RenameConfig(rules=[rule])
    diffs = [_diff("prod/a"), _diff("dev/b"), _diff("prod/c")]
    results = rename_diffs(diffs, config)
    assert results[0].renamed_path == "uat/a"
    assert results[1].renamed_path == "dev/b"
    assert results[2].renamed_path == "uat/c"
