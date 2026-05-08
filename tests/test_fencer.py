"""Tests for vaultdiff.fencer."""

import pytest
from vaultdiff.fencer import FenceConfig, FenceRule, Fencer


def _make_fencer(**kwargs) -> Fencer:
    config = FenceConfig(**kwargs)
    return Fencer(config)


def test_no_rules_allows_everything_by_default():
    fencer = _make_fencer()
    result = fencer.check("secret/prod/db")
    assert result.allowed is True
    assert "default allow" in result.reason


def test_no_rules_default_deny_blocks_everything():
    fencer = _make_fencer(default_allow=False)
    result = fencer.check("secret/prod/db")
    assert result.allowed is False
    assert "default deny" in result.reason


def test_prefix_rule_allows_matching_path():
    rule = FenceRule(prefix="secret/prod/", allow=True)
    fencer = Fencer(FenceConfig(rules=[rule], default_allow=False))
    result = fencer.check("secret/prod/db")
    assert result.allowed is True
    assert "allow" in result.reason


def test_prefix_rule_denies_matching_path():
    rule = FenceRule(prefix="secret/internal/", allow=False)
    fencer = Fencer(FenceConfig(rules=[rule], default_allow=True))
    result = fencer.check("secret/internal/keys")
    assert result.allowed is False
    assert "deny" in result.reason


def test_glob_rule_matches_pattern():
    rule = FenceRule(glob="secret/*/db", allow=True)
    fencer = Fencer(FenceConfig(rules=[rule], default_allow=False))
    assert fencer.check("secret/prod/db").allowed is True
    assert fencer.check("secret/staging/db").allowed is True
    assert fencer.check("secret/prod/cache").allowed is False


def test_first_matching_rule_wins():
    rules = [
        FenceRule(prefix="secret/prod/", allow=False),
        FenceRule(prefix="secret/", allow=True),
    ]
    fencer = Fencer(FenceConfig(rules=rules))
    # prod matches first rule → denied
    assert fencer.check("secret/prod/db").allowed is False
    # staging skips first rule, matches second → allowed
    assert fencer.check("secret/staging/db").allowed is True


def test_filter_paths_returns_only_allowed():
    rule = FenceRule(prefix="secret/internal/", allow=False)
    fencer = Fencer(FenceConfig(rules=[rule], default_allow=True))
    paths = ["secret/prod/db", "secret/internal/keys", "secret/staging/api"]
    result = fencer.filter_paths(paths)
    assert result == ["secret/prod/db", "secret/staging/api"]


def test_fence_config_from_dict_parses_rules():
    data = {
        "default_allow": False,
        "rules": [
            {"prefix": "secret/prod/", "allow": True},
            {"glob": "secret/*/db", "allow": False},
        ],
    }
    config = FenceConfig.from_dict(data)
    assert config.default_allow is False
    assert len(config.rules) == 2
    assert config.rules[0].prefix == "secret/prod/"
    assert config.rules[1].glob == "secret/*/db"
    assert config.rules[1].allow is False


def test_fence_config_from_dict_empty():
    config = FenceConfig.from_dict({})
    assert config.default_allow is True
    assert config.rules == []


def test_fence_result_to_dict():
    fencer = _make_fencer()
    result = fencer.check("secret/prod/db")
    d = result.to_dict()
    assert d["path"] == "secret/prod/db"
    assert isinstance(d["allowed"], bool)
    assert isinstance(d["reason"], str)
