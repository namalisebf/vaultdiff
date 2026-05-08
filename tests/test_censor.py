"""Tests for vaultdiff.censor."""
import pytest
from vaultdiff.censor import (
    CensorRule,
    CensorConfig,
    CensoredDiff,
    censor_diff,
    _PLACEHOLDER,
)
from vaultdiff.differ import SecretDiff


def _make_diff(
    path="secret/app",
    changed=None,
    only_in_left=None,
    only_in_right=None,
) -> SecretDiff:
    return SecretDiff(
        path=path,
        changed=changed or {},
        only_in_left=only_in_left or {},
        only_in_right=only_in_right or {},
    )


def test_censor_rule_glob_matches_key():
    rule = CensorRule(key_pattern="*password*")
    assert rule.matches_key("db_password") is True
    assert rule.matches_key("username") is False


def test_censor_rule_regex_matches_key():
    rule = CensorRule(key_pattern=r"^secret_", mode="regex")
    assert rule.matches_key("secret_token") is True
    assert rule.matches_key("public_key") is False


def test_censor_rule_path_pattern_filters_path():
    rule = CensorRule(key_pattern="token", path_pattern="secret/prod/*")
    assert rule.matches_path("secret/prod/app") is True
    assert rule.matches_path("secret/staging/app") is False


def test_censor_rule_no_path_pattern_always_matches_path():
    rule = CensorRule(key_pattern="token")
    assert rule.matches_path("any/path") is True


def test_censor_config_from_dict_parses_rules():
    data = {
        "rules": [
            {"key_pattern": "*pass*"},
            {"key_pattern": r"^api", "mode": "regex", "path_pattern": "secret/*"},
        ],
        "placeholder": "[HIDDEN]",
    }
    config = CensorConfig.from_dict(data)
    assert len(config.rules) == 2
    assert config.placeholder == "[HIDDEN]"
    assert config.rules[1].mode == "regex"


def test_censor_config_from_dict_empty():
    config = CensorConfig.from_dict({})
    assert config.rules == []
    assert config.placeholder == _PLACEHOLDER


def test_censor_diff_no_rules_preserves_values():
    diff = _make_diff(
        changed={"key": {"left": "a", "right": "b"}},
        only_in_left={"old": "1"},
        only_in_right={"new": "2"},
    )
    config = CensorConfig()
    result = censor_diff(diff, config)
    assert result.changed["key"]["left"] == "a"
    assert result.only_in_left["old"] == "1"
    assert result.only_in_right["new"] == "2"


def test_censor_diff_masks_changed_sensitive_key():
    diff = _make_diff(changed={"password": {"left": "hunter2", "right": "secret"}})
    config = CensorConfig(rules=[CensorRule(key_pattern="password")])
    result = censor_diff(diff, config)
    assert result.changed["password"]["left"] == _PLACEHOLDER
    assert result.changed["password"]["right"] == _PLACEHOLDER


def test_censor_diff_masks_only_in_left_and_right():
    diff = _make_diff(
        only_in_left={"api_key": "abc"},
        only_in_right={"api_key": "xyz"},
    )
    config = CensorConfig(rules=[CensorRule(key_pattern="api_key")])
    result = censor_diff(diff, config)
    assert result.only_in_left["api_key"] == _PLACEHOLDER
    assert result.only_in_right["api_key"] == _PLACEHOLDER


def test_censor_diff_path_scoped_rule_does_not_censor_other_paths():
    diff = _make_diff(
        path="secret/staging/app",
        changed={"token": {"left": "old", "right": "new"}},
    )
    config = CensorConfig(
        rules=[CensorRule(key_pattern="token", path_pattern="secret/prod/*")]
    )
    result = censor_diff(diff, config)
    assert result.changed["token"]["left"] == "old"
    assert result.changed["token"]["right"] == "new"


def test_censored_diff_has_differences_true_when_changed():
    cd = CensoredDiff(
        path="p",
        changed={"k": {"left": "a", "right": "b"}},
        only_in_left={},
        only_in_right={},
    )
    assert cd.has_differences() is True


def test_censored_diff_has_differences_false_when_clean():
    cd = CensoredDiff(path="p", changed={}, only_in_left={}, only_in_right={})
    assert cd.has_differences() is False


def test_censored_diff_to_dict_keys():
    cd = CensoredDiff(path="p", changed={}, only_in_left={}, only_in_right={})
    d = cd.to_dict()
    assert set(d.keys()) == {"path", "changed", "only_in_left", "only_in_right"}
