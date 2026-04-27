"""Tests for vaultdiff.policy."""
import pytest
from vaultdiff.differ import SecretDiff
from vaultdiff.policy import PolicyChecker, PolicyConfig, PolicyViolation


def _make_diff(
    path="secret/app",
    changed=None,
    only_left=None,
    only_right=None,
    left_data=None,
    right_data=None,
) -> SecretDiff:
    return SecretDiff(
        path=path,
        changed_keys=changed or [],
        only_in_left=only_left or [],
        only_in_right=only_right or [],
        left_data=left_data or {},
        right_data=right_data or {},
    )


def test_no_violations_when_no_rules():
    checker = PolicyChecker(PolicyConfig())
    diff = _make_diff(
        changed=[("DB_PASSWORD", ("old", "new"))],
        right_data={"DB_PASSWORD": "new"},
    )
    assert checker.check_diff(diff) == []


def test_required_key_pattern_violation():
    checker = PolicyChecker(PolicyConfig(required_key_pattern=r"^[A-Z_]+$"))
    diff = _make_diff(
        only_right=["bad-key"],
        right_data={"bad-key": "value"},
    )
    violations = checker.check_diff(diff)
    assert len(violations) == 1
    assert violations[0].rule == "required_key_pattern"
    assert violations[0].key == "bad-key"


def test_required_key_pattern_passes_valid_key():
    checker = PolicyChecker(PolicyConfig(required_key_pattern=r"^[A-Z_]+$"))
    diff = _make_diff(
        only_right=["VALID_KEY"],
        right_data={"VALID_KEY": "v"},
    )
    assert checker.check_diff(diff) == []


def test_forbidden_key_pattern_violation():
    checker = PolicyChecker(PolicyConfig(forbidden_key_pattern=r"(?i)secret"))
    diff = _make_diff(
        only_right=["my_secret_key"],
        right_data={"my_secret_key": "x"},
    )
    violations = checker.check_diff(diff)
    assert any(v.rule == "forbidden_key_pattern" for v in violations)


def test_disallow_empty_values():
    checker = PolicyChecker(PolicyConfig(disallow_empty_values=True))
    diff = _make_diff(
        only_right=["EMPTY"],
        right_data={"EMPTY": ""},
    )
    violations = checker.check_diff(diff)
    assert len(violations) == 1
    assert violations[0].rule == "disallow_empty_values"


def test_max_value_length():
    checker = PolicyChecker(PolicyConfig(max_value_length=10))
    diff = _make_diff(
        changed=[("TOKEN", ("short", "a" * 20))],
        right_data={"TOKEN": "a" * 20},
    )
    violations = checker.check_diff(diff)
    assert len(violations) == 1
    assert violations[0].rule == "max_value_length"


def test_max_value_length_within_limit():
    checker = PolicyChecker(PolicyConfig(max_value_length=50))
    diff = _make_diff(
        changed=[("TOKEN", ("old", "new"))],
        right_data={"TOKEN": "new"},
    )
    assert checker.check_diff(diff) == []


def test_violation_to_dict():
    v = PolicyViolation(path="p", key="k", rule="r", message="m")
    d = v.to_dict()
    assert d == {"path": "p", "key": "k", "rule": "r", "message": "m"}


def test_multiple_violations_accumulated():
    checker = PolicyChecker(PolicyConfig(
        required_key_pattern=r"^[A-Z_]+$",
        disallow_empty_values=True,
    ))
    diff = _make_diff(
        only_right=["bad-key"],
        right_data={"bad-key": ""},
    )
    violations = checker.check_diff(diff)
    rules = {v.rule for v in violations}
    assert "required_key_pattern" in rules
    assert "disallow_empty_values" in rules
