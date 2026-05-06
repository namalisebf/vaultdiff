"""Integration tests for classifier — exercises full classify_diffs pipeline."""
from __future__ import annotations

from vaultdiff.classifier import (
    ClassifierConfig,
    SENSITIVITY_TIERS,
    classify_diffs,
)
from vaultdiff.differ import SecretDiff


def _diff(path, **kwargs) -> SecretDiff:
    return SecretDiff(
        path=path,
        changed_keys=kwargs.get("changed", {}),
        only_in_left=kwargs.get("left", {}),
        only_in_right=kwargs.get("right", {}),
    )


def test_all_clean_paths_are_low_tier():
    diffs = [_diff(f"secret/path{i}") for i in range(5)]
    results = classify_diffs(diffs)
    assert all(r.tier == "low" for r in results)


def test_critical_path_sorts_first():
    diffs = [
        _diff("secret/info", changed={"region": ("a", "b")}),
        _diff("secret/creds", changed={"db_password": ("x", "y")}),
        _diff("secret/tokens", changed={"auth_token": ("p", "q")}),
    ]
    results = classify_diffs(diffs)
    assert results[0].tier == "critical"
    assert results[1].tier == "high"
    assert results[2].tier == "low"


def test_custom_config_overrides_defaults():
    cfg = ClassifierConfig.from_dict({"rules": {"critical": ["*pin*"], "low": ["*"]}})
    d = _diff("secret/card", changed={"pin_code": ("1234", "5678")})
    results = classify_diffs([d], config=cfg)
    assert results[0].tier == "critical"


def test_only_in_right_keys_contribute_to_tier():
    d = _diff("secret/new", right={"master_key": "abc"})
    results = classify_diffs([d])
    assert results[0].tier == "critical"


def test_classified_path_diff_reference_preserved():
    d = _diff("secret/ref", changed={"token": ("a", "b")})
    results = classify_diffs([d])
    assert results[0].diff is d


def test_sensitivity_tiers_ordering():
    """Ensure SENSITIVITY_TIERS is ordered most-to-least severe."""
    assert SENSITIVITY_TIERS.index("critical") < SENSITIVITY_TIERS.index("high")
    assert SENSITIVITY_TIERS.index("high") < SENSITIVITY_TIERS.index("medium")
    assert SENSITIVITY_TIERS.index("medium") < SENSITIVITY_TIERS.index("low")
