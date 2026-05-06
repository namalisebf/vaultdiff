"""Unit tests for vaultdiff.classifier."""
from __future__ import annotations

from vaultdiff.classifier import (
    ClassifierConfig,
    ClassifiedPath,
    SENSITIVITY_TIERS,
    _tier_for_key,
    classify_diffs,
)
from vaultdiff.differ import SecretDiff


def _diff(path: str, changed=None, left=None, right=None) -> SecretDiff:
    return SecretDiff(
        path=path,
        changed_keys=changed or {},
        only_in_left=left or {},
        only_in_right=right or {},
    )


def test_tier_for_key_critical():
    assert _tier_for_key("db_password", ClassifierConfig().rules) == "critical"


def test_tier_for_key_high():
    assert _tier_for_key("api_key", ClassifierConfig().rules) == "high"


def test_tier_for_key_medium():
    assert _tier_for_key("ssl_cert", ClassifierConfig().rules) == "medium"


def test_tier_for_key_low_fallback():
    assert _tier_for_key("region", ClassifierConfig().rules) == "low"


def test_classify_empty_list():
    result = classify_diffs([])
    assert result == []


def test_classify_assigns_critical_tier():
    d = _diff("secret/db", changed={"password": ("old", "new")})
    results = classify_diffs([d])
    assert len(results) == 1
    assert results[0].tier == "critical"
    assert results[0].path == "secret/db"


def test_classify_assigns_low_tier_for_plain_key():
    d = _diff("secret/config", changed={"region": ("us-east-1", "eu-west-1")})
    results = classify_diffs([d])
    assert results[0].tier == "low"


def test_classify_picks_highest_tier_among_keys():
    d = _diff(
        "secret/mixed",
        changed={"region": ("a", "b"), "api_key": ("x", "y")},
    )
    results = classify_diffs([d])
    assert results[0].tier == "high"


def test_classify_sorted_by_tier_severity():
    d_low = _diff("secret/low", changed={"region": ("a", "b")})
    d_critical = _diff("secret/crit", changed={"master_key": ("a", "b")})
    results = classify_diffs([d_low, d_critical])
    assert results[0].tier == "critical"
    assert results[1].tier == "low"


def test_classify_includes_only_in_left_keys():
    d = _diff("secret/gone", left={"token": "abc"})
    results = classify_diffs([d])
    assert results[0].tier == "high"
    assert "token" in results[0].matched_keys


def test_classifier_config_from_dict_custom_rules():
    cfg = ClassifierConfig.from_dict({"rules": {"critical": ["*pin*"]}})
    assert "*pin*" in cfg.rules["critical"]


def test_classified_path_to_dict():
    cp = ClassifiedPath(path="secret/x", tier="high", matched_keys=["api_key"])
    d = cp.to_dict()
    assert d["path"] == "secret/x"
    assert d["tier"] == "high"
    assert "api_key" in d["matched_keys"]
