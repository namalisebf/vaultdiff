"""Tests for vaultdiff.stencil."""
from unittest.mock import MagicMock

import pytest

from vaultdiff.differ import SecretDiff
from vaultdiff.stencil import (
    StencilConfig,
    StencilRule,
    apply_stencil,
)


def _make_diff(
    path="secret/app",
    changed=None,
    only_left=None,
    only_right=None,
) -> SecretDiff:
    diff = MagicMock(spec=SecretDiff)
    diff.path = path

    if changed:
        entries = {}
        for k, (l, r) in changed.items():
            e = MagicMock()
            e.left_value = l
            e.right_value = r
            entries[k] = e
        diff.changed_keys = entries
    else:
        diff.changed_keys = {}

    diff.only_in_left = only_left or {}
    diff.only_in_right = only_right or {}
    return diff


def test_stencil_config_from_dict_empty():
    cfg = StencilConfig.from_dict({})
    assert cfg.rules == []


def test_stencil_config_from_dict_with_rules():
    cfg = StencilConfig.from_dict({
        "rules": [
            {"key_pattern": "password", "hidden": True},
            {"key_pattern": "db_*", "alias": "database_key"},
        ]
    })
    assert len(cfg.rules) == 2
    assert cfg.rules[0].hidden is True
    assert cfg.rules[1].alias == "database_key"


def test_stencil_rule_matches_glob():
    rule = StencilRule(key_pattern="secret_*")
    assert rule.matches("secret_token") is True
    assert rule.matches("public_key") is False


def test_apply_stencil_no_rules_passes_all_keys():
    diff = _make_diff(changed={"api_key": ("old", "new")}, only_left={"removed": "v"})
    result = apply_stencil(diff, StencilConfig())
    assert "api_key" in result.changed_keys
    assert "removed" in result.only_in_left


def test_apply_stencil_hidden_key_removed():
    diff = _make_diff(changed={"password": ("old", "new"), "host": ("a", "b")})
    cfg = StencilConfig(rules=[StencilRule(key_pattern="password", hidden=True)])
    result = apply_stencil(diff, cfg)
    assert "password" not in result.changed_keys
    assert "host" in result.changed_keys


def test_apply_stencil_alias_renames_key():
    diff = _make_diff(only_right={"db_pass": "secret"})
    cfg = StencilConfig(rules=[StencilRule(key_pattern="db_*", alias="database_credential")])
    result = apply_stencil(diff, cfg)
    assert "database_credential" in result.only_in_right
    assert "db_pass" not in result.only_in_right


def test_apply_stencil_hidden_only_in_left():
    diff = _make_diff(only_left={"token": "abc", "name": "app"})
    cfg = StencilConfig(rules=[StencilRule(key_pattern="token", hidden=True)])
    result = apply_stencil(diff, cfg)
    assert "token" not in result.only_in_left
    assert "name" in result.only_in_left


def test_stencilled_path_has_differences_true():
    diff = _make_diff(changed={"x": ("1", "2")})
    result = apply_stencil(diff, StencilConfig())
    assert result.has_differences() is True


def test_stencilled_path_has_differences_false_when_all_hidden():
    diff = _make_diff(changed={"secret": ("a", "b")})
    cfg = StencilConfig(rules=[StencilRule(key_pattern="secret", hidden=True)])
    result = apply_stencil(diff, cfg)
    assert result.has_differences() is False


def test_stencilled_path_to_dict_keys():
    diff = _make_diff(path="secret/svc", changed={"key": ("v1", "v2")})
    result = apply_stencil(diff, StencilConfig())
    d = result.to_dict()
    assert set(d.keys()) == {"path", "changed_keys", "only_in_left", "only_in_right"}
    assert d["path"] == "secret/svc"
