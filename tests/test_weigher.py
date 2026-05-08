"""Unit tests for vaultdiff.weigher."""
from __future__ import annotations

from unittest.mock import MagicMock

from vaultdiff.differ import SecretDiff
from vaultdiff.weigher import WeightConfig, WeightRule, WeighedPath, weigh_diffs


def _diff(path: str) -> SecretDiff:
    d = MagicMock(spec=SecretDiff)
    d.path = path
    return d


# --- WeightRule.matches ---

def test_weight_rule_glob_matches():
    rule = WeightRule(pattern="prod/*", weight=5.0)
    assert rule.matches("prod/db") is True
    assert rule.matches("staging/db") is False


def test_weight_rule_prefix_matches():
    rule = WeightRule(pattern="prod/", weight=3.0, mode="prefix")
    assert rule.matches("prod/api") is True
    assert rule.matches("staging/api") is False


def test_weight_rule_regex_matches():
    rule = WeightRule(pattern=r"^prod/", weight=4.0, mode="regex")
    assert rule.matches("prod/db") is True
    assert rule.matches("dev/db") is False


# --- WeightConfig.from_dict ---

def test_weight_config_from_dict():
    cfg = WeightConfig.from_dict({
        "rules": [{"pattern": "prod/*", "weight": "5", "mode": "glob"}],
        "default_weight": "2.0",
    })
    assert len(cfg.rules) == 1
    assert cfg.rules[0].weight == 5.0
    assert cfg.default_weight == 2.0


def test_weight_config_from_dict_empty():
    cfg = WeightConfig.from_dict({})
    assert cfg.rules == []
    assert cfg.default_weight == 1.0


# --- weigh_diffs ---

def test_weigh_diffs_no_rules_uses_default():
    config = WeightConfig(rules=[], default_weight=1.0)
    diffs = [_diff("prod/db"), _diff("staging/api")]
    result = weigh_diffs(diffs, config)
    assert all(wp.weight == 1.0 for wp in result)
    assert all(wp.matched_rule is None for wp in result)


def test_weigh_diffs_matching_rule_applied():
    config = WeightConfig(
        rules=[WeightRule(pattern="prod/*", weight=10.0)],
        default_weight=1.0,
    )
    result = weigh_diffs([_diff("prod/db"), _diff("staging/api")], config)
    by_path = {wp.path: wp for wp in result}
    assert by_path["prod/db"].weight == 10.0
    assert by_path["prod/db"].matched_rule == "prod/*"
    assert by_path["staging/api"].weight == 1.0
    assert by_path["staging/api"].matched_rule is None


def test_weigh_diffs_sorted_descending():
    config = WeightConfig(
        rules=[
            WeightRule(pattern="prod/*", weight=5.0),
            WeightRule(pattern="staging/*", weight=2.0),
        ],
        default_weight=1.0,
    )
    diffs = [_diff("staging/x"), _diff("dev/x"), _diff("prod/x")]
    result = weigh_diffs(diffs, config)
    weights = [wp.weight for wp in result]
    assert weights == sorted(weights, reverse=True)


def test_weigh_diffs_first_rule_wins():
    config = WeightConfig(
        rules=[
            WeightRule(pattern="prod/*", weight=9.0),
            WeightRule(pattern="prod/db", weight=1.0),
        ],
        default_weight=1.0,
    )
    result = weigh_diffs([_diff("prod/db")], config)
    assert result[0].weight == 9.0
    assert result[0].matched_rule == "prod/*"


def test_weighed_path_to_dict():
    wp = WeighedPath(path="prod/db", weight=5.0, matched_rule="prod/*")
    d = wp.to_dict()
    assert d["path"] == "prod/db"
    assert d["weight"] == 5.0
    assert d["matched_rule"] == "prod/*"
