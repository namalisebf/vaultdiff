"""Unit tests for vaultdiff.validator."""
from __future__ import annotations

import pytest

from vaultdiff.differ import SecretDiff
from vaultdiff.validator import (
    ValidationConfig,
    ValidationRule,
    ValidationViolation,
    Validator,
)


def _make_diff(
    path: str = "secret/app",
    changed: dict | None = None,
    only_in_left: dict | None = None,
    only_in_right: dict | None = None,
) -> SecretDiff:
    return SecretDiff(
        path=path,
        changed=changed or {},
        only_in_left=only_in_left or {},
        only_in_right=only_in_right or {},
    )


def test_no_rules_produces_no_violations():
    config = ValidationConfig(rules=[])
    validator = Validator(config)
    diff = _make_diff(changed={"key": ("a", "b")})
    assert validator.validate(diff) == []


def test_required_key_missing_raises_violation():
    rule = ValidationRule(path_glob="secret/*", required_keys=["db_password"])
    config = ValidationConfig(rules=[rule])
    validator = Validator(config)
    diff = _make_diff(path="secret/app", changed={"api_key": ("x", "y")})
    violations = validator.validate(diff)
    assert len(violations) == 1
    assert "db_password" in violations[0].message


def test_required_key_present_passes():
    rule = ValidationRule(path_glob="secret/*", required_keys=["db_password"])
    config = ValidationConfig(rules=[rule])
    validator = Validator(config)
    diff = _make_diff(path="secret/app", only_in_right={"db_password": "secret"})
    assert validator.validate(diff) == []


def test_forbidden_key_present_raises_violation():
    rule = ValidationRule(path_glob="secret/*", forbidden_keys=["debug_token"])
    config = ValidationConfig(rules=[rule])
    validator = Validator(config)
    diff = _make_diff(path="secret/app", only_in_right={"debug_token": "val"})
    violations = validator.validate(diff)
    assert len(violations) == 1
    assert "debug_token" in violations[0].message


def test_forbidden_key_absent_passes():
    rule = ValidationRule(path_glob="secret/*", forbidden_keys=["debug_token"])
    config = ValidationConfig(rules=[rule])
    validator = Validator(config)
    diff = _make_diff(path="secret/app", changed={"safe_key": ("a", "b")})
    assert validator.validate(diff) == []


def test_key_pattern_violation_when_key_does_not_match():
    rule = ValidationRule(path_glob="secret/*", key_pattern=r"^[a-z_]+$")
    config = ValidationConfig(rules=[rule])
    validator = Validator(config)
    diff = _make_diff(path="secret/app", changed={"BAD-KEY": ("a", "b")})
    violations = validator.validate(diff)
    assert any("BAD-KEY" in v.message for v in violations)


def test_key_pattern_passes_when_all_keys_match():
    rule = ValidationRule(path_glob="secret/*", key_pattern=r"^[a-z_]+$")
    config = ValidationConfig(rules=[rule])
    validator = Validator(config)
    diff = _make_diff(path="secret/app", changed={"good_key": ("a", "b")})
    assert validator.validate(diff) == []


def test_rule_does_not_apply_to_non_matching_path():
    rule = ValidationRule(path_glob="secret/prod/*", required_keys=["tls_cert"])
    config = ValidationConfig(rules=[rule])
    validator = Validator(config)
    diff = _make_diff(path="secret/dev/app", changed={"key": ("a", "b")})
    assert validator.validate(diff) == []


def test_validate_all_aggregates_across_diffs():
    rule = ValidationRule(path_glob="secret/*", required_keys=["token"])
    config = ValidationConfig(rules=[rule])
    validator = Validator(config)
    diffs = [
        _make_diff(path="secret/app1"),
        _make_diff(path="secret/app2"),
    ]
    violations = validator.validate_all(diffs)
    assert len(violations) == 2


def test_violation_to_dict_has_expected_keys():
    v = ValidationViolation(path="secret/app", rule_glob="secret/*", message="Missing key")
    d = v.to_dict()
    assert set(d.keys()) == {"path", "rule", "message"}


def test_config_from_dict_parses_rules():
    data = {
        "rules": [
            {"path": "secret/*", "required_keys": ["token"], "forbidden_keys": ["debug"]}
        ]
    }
    config = ValidationConfig.from_dict(data)
    assert len(config.rules) == 1
    assert config.rules[0].required_keys == ["token"]
    assert config.rules[0].forbidden_keys == ["debug"]


def test_config_from_dict_empty_produces_no_rules():
    config = ValidationConfig.from_dict({})
    assert config.rules == []
