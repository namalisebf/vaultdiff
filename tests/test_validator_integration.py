"""Integration tests for validator — exercises Validator with real SecretDiff objects."""
from __future__ import annotations

import pytest

from vaultdiff.differ import SecretDiff
from vaultdiff.validator import ValidationConfig, ValidationRule, Validator


def _diff(path="secret/app", changed=None, only_in_left=None, only_in_right=None):
    return SecretDiff(
        path=path,
        changed=changed or {},
        only_in_left=only_in_left or {},
        only_in_right=only_in_right or {},
    )


def test_multiple_rules_all_apply_to_same_path():
    rules = [
        ValidationRule(path_glob="secret/*", required_keys=["token"]),
        ValidationRule(path_glob="secret/*", forbidden_keys=["debug"]),
    ]
    config = ValidationConfig(rules=rules)
    validator = Validator(config)
    diff = _diff(path="secret/app", only_in_right={"debug": "true"})
    violations = validator.validate(diff)
    # Missing 'token' + forbidden 'debug'
    assert len(violations) == 2


def test_only_first_matching_glob_does_not_skip_others():
    """All matching rules should be applied, not just the first."""
    rules = [
        ValidationRule(path_glob="secret/prod/*", required_keys=["tls_cert"]),
        ValidationRule(path_glob="secret/prod/*", required_keys=["db_password"]),
    ]
    config = ValidationConfig(rules=rules)
    validator = Validator(config)
    diff = _diff(path="secret/prod/app")
    violations = validator.validate(diff)
    messages = [v.message for v in violations]
    assert any("tls_cert" in m for m in messages)
    assert any("db_password" in m for m in messages)


def test_validate_all_returns_flat_list():
    rule = ValidationRule(path_glob="secret/*", required_keys=["api_key"])
    config = ValidationConfig(rules=[rule])
    validator = Validator(config)
    diffs = [_diff(path=f"secret/svc{i}") for i in range(3)]
    violations = validator.validate_all(diffs)
    assert len(violations) == 3
    paths = {v.path for v in violations}
    assert paths == {"secret/svc0", "secret/svc1", "secret/svc2"}


def test_key_present_in_changed_satisfies_required():
    rule = ValidationRule(path_glob="secret/*", required_keys=["password"])
    config = ValidationConfig(rules=[rule])
    validator = Validator(config)
    diff = _diff(path="secret/db", changed={"password": ("old", "new")})
    assert validator.validate(diff) == []


def test_key_present_in_only_in_left_satisfies_required():
    rule = ValidationRule(path_glob="secret/*", required_keys=["legacy_key"])
    config = ValidationConfig(rules=[rule])
    validator = Validator(config)
    diff = _diff(path="secret/app", only_in_left={"legacy_key": "val"})
    assert validator.validate(diff) == []
