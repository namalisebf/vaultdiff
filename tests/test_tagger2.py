"""Tests for vaultdiff.tagger2."""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from vaultdiff.differ import SecretDiff
from vaultdiff.tagger2 import (
    EnvTagConfig,
    EnvTagRule,
    EnvTaggedPath,
    tag_diffs,
)


def _diff(path: str, changed=None, only_left=None, only_right=None) -> SecretDiff:
    d = MagicMock(spec=SecretDiff)
    d.path = path
    d.changed_keys = changed or {}
    d.only_in_left = only_left or {}
    d.only_in_right = only_right or {}
    d.has_differences.return_value = bool(
        (changed or {}) or (only_left or {}) or (only_right or {})
    )
    return d


def test_tag_rule_glob_matches():
    rule = EnvTagRule(pattern="secret/prod/*", tag="production")
    assert rule.matches("secret/prod/db") is True
    assert rule.matches("secret/staging/db") is False


def test_tag_rule_prefix_matches():
    rule = EnvTagRule(pattern="secret/prod", tag="production", mode="prefix")
    assert rule.matches("secret/prod/db") is True
    assert rule.matches("secret/staging") is False


def test_tag_rule_env_filter_skips_wrong_env():
    rule = EnvTagRule(pattern="secret/*", tag="prod-tag", env="prod")
    assert rule.matches("secret/db", env="prod") is True
    assert rule.matches("secret/db", env="staging") is False
    assert rule.matches("secret/db", env=None) is False


def test_tag_rule_no_env_applies_to_all():
    rule = EnvTagRule(pattern="secret/*", tag="any-tag", env=None)
    assert rule.matches("secret/db", env="prod") is True
    assert rule.matches("secret/db", env="staging") is True


def test_env_tag_config_from_dict():
    data = {
        "rules": [
            {"pattern": "secret/prod/*", "tag": "prod", "env": "prod"},
            {"pattern": "secret/staging/*", "tag": "staging", "mode": "prefix"},
        ],
        "default_tag": "unknown",
    }
    config = EnvTagConfig.from_dict(data)
    assert len(config.rules) == 2
    assert config.default_tag == "unknown"
    assert config.rules[0].env == "prod"
    assert config.rules[1].mode == "prefix"


def test_env_tag_config_from_dict_empty():
    config = EnvTagConfig.from_dict({})
    assert config.rules == []
    assert config.default_tag == "untagged"


def test_tag_diffs_no_rules_uses_default():
    config = EnvTagConfig(rules=[], default_tag="fallback")
    diffs = [_diff("secret/app/key")]
    result = tag_diffs(diffs, config)
    assert len(result) == 1
    assert result[0].tag == "fallback"
    assert result[0].path == "secret/app/key"


def test_tag_diffs_first_matching_rule_wins():
    config = EnvTagConfig(
        rules=[
            EnvTagRule(pattern="secret/prod/*", tag="prod"),
            EnvTagRule(pattern="secret/*", tag="any"),
        ]
    )
    diffs = [_diff("secret/prod/db")]
    result = tag_diffs(diffs, config)
    assert result[0].tag == "prod"


def test_tag_diffs_env_passed_to_rule():
    config = EnvTagConfig(
        rules=[EnvTagRule(pattern="secret/*", tag="env-specific", env="prod")]
    )
    diffs = [_diff("secret/db")]
    result_prod = tag_diffs(diffs, config, env="prod")
    result_staging = tag_diffs(diffs, config, env="staging")
    assert result_prod[0].tag == "env-specific"
    assert result_staging[0].tag == "untagged"


def test_env_tagged_path_to_dict_keys():
    diff = _diff("secret/db", changed={"key": ("a", "b")})
    tagged = EnvTaggedPath(path="secret/db", tag="prod", diff=diff)
    d = tagged.to_dict()
    assert "path" in d
    assert "tag" in d
    assert "has_differences" in d
    assert d["has_differences"] is True
