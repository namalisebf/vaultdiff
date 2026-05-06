"""Tests for vaultdiff.scoper."""
import pytest
from vaultdiff.scoper import ScopeConfig, Scoper, ScopedPath


def test_scope_config_from_dict():
    cfg = ScopeConfig.from_dict(
        {"allowed_prefixes": ["secret/prod"], "denied_prefixes": ["secret/prod/internal"]}
    )
    assert cfg.allowed_prefixes == ["secret/prod"]
    assert cfg.denied_prefixes == ["secret/prod/internal"]


def test_scope_config_from_dict_empty():
    cfg = ScopeConfig.from_dict({})
    assert cfg.allowed_prefixes == []
    assert cfg.denied_prefixes == []


def test_no_rules_allows_everything():
    scoper = Scoper()
    assert scoper.is_allowed("secret/anything") is True
    assert scoper.is_allowed("kv/data/foo") is True


def test_allowed_prefix_permits_matching_path():
    scoper = Scoper(ScopeConfig(allowed_prefixes=["secret/prod"]))
    assert scoper.is_allowed("secret/prod/db") is True
    assert scoper.is_allowed("secret/prod") is True


def test_allowed_prefix_blocks_non_matching_path():
    scoper = Scoper(ScopeConfig(allowed_prefixes=["secret/prod"]))
    assert scoper.is_allowed("secret/staging/db") is False


def test_denied_prefix_blocks_path():
    scoper = Scoper(ScopeConfig(denied_prefixes=["secret/prod/internal"]))
    assert scoper.is_allowed("secret/prod/internal/creds") is False


def test_denied_prefix_does_not_block_other_paths():
    scoper = Scoper(ScopeConfig(denied_prefixes=["secret/prod/internal"]))
    assert scoper.is_allowed("secret/prod/public") is True


def test_denied_takes_precedence_over_allowed():
    scoper = Scoper(ScopeConfig(
        allowed_prefixes=["secret/prod"],
        denied_prefixes=["secret/prod/internal"],
    ))
    assert scoper.is_allowed("secret/prod/api") is True
    assert scoper.is_allowed("secret/prod/internal/key") is False


def test_glob_pattern_in_allowed_prefixes():
    scoper = Scoper(ScopeConfig(allowed_prefixes=["secret/*/config"]))
    assert scoper.is_allowed("secret/prod/config") is True
    assert scoper.is_allowed("secret/staging/config") is True
    assert scoper.is_allowed("secret/prod/data") is False


def test_evaluate_returns_scoped_path_allowed():
    scoper = Scoper(ScopeConfig(allowed_prefixes=["secret/prod"]))
    result = scoper.evaluate("secret/prod/db")
    assert isinstance(result, ScopedPath)
    assert result.allowed is True
    assert result.reason == "within scope"


def test_evaluate_returns_scoped_path_denied_by_rule():
    scoper = Scoper(ScopeConfig(denied_prefixes=["secret/prod/internal"]))
    result = scoper.evaluate("secret/prod/internal/creds")
    assert result.allowed is False
    assert "denied" in result.reason


def test_evaluate_returns_scoped_path_not_in_allowed():
    scoper = Scoper(ScopeConfig(allowed_prefixes=["secret/prod"]))
    result = scoper.evaluate("secret/staging/db")
    assert result.allowed is False
    assert "allowed" in result.reason


def test_scoped_path_to_dict():
    sp = ScopedPath(path="secret/prod/db", allowed=True, reason="within scope")
    d = sp.to_dict()
    assert d == {"path": "secret/prod/db", "allowed": True, "reason": "within scope"}


def test_filter_paths_removes_out_of_scope():
    scoper = Scoper(ScopeConfig(allowed_prefixes=["secret/prod"]))
    paths = ["secret/prod/db", "secret/staging/db", "secret/prod/api"]
    result = scoper.filter_paths(paths)
    assert result == ["secret/prod/db", "secret/prod/api"]


def test_filter_paths_empty_input():
    scoper = Scoper(ScopeConfig(allowed_prefixes=["secret/prod"]))
    assert scoper.filter_paths([]) == []
