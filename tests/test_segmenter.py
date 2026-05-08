"""Tests for vaultdiff.segmenter."""
from __future__ import annotations

from unittest.mock import MagicMock

from vaultdiff.differ import SecretDiff
from vaultdiff.segmenter import (
    Segment,
    SegmentConfig,
    SegmentRule,
    segment_diffs,
)


def _diff(path: str, changed: bool = False) -> SecretDiff:
    d = MagicMock(spec=SecretDiff)
    d.path = path
    d.has_differences = changed
    return d


# ---------------------------------------------------------------------------
# SegmentRule
# ---------------------------------------------------------------------------

def test_segment_rule_prefix_matches():
    rule = SegmentRule(name="infra", prefix="secret/infra/")
    assert rule.matches("secret/infra/db") is True


def test_segment_rule_prefix_no_match():
    rule = SegmentRule(name="infra", prefix="secret/infra/")
    assert rule.matches("secret/app/db") is False


def test_segment_rule_glob_matches():
    rule = SegmentRule(name="prod", glob="*/prod/*")
    assert rule.matches("secret/prod/api") is True


def test_segment_rule_glob_no_match():
    rule = SegmentRule(name="prod", glob="*/prod/*")
    assert rule.matches("secret/staging/api") is False


# ---------------------------------------------------------------------------
# SegmentConfig.from_dict
# ---------------------------------------------------------------------------

def test_segment_config_from_dict():
    cfg = SegmentConfig.from_dict({
        "rules": [
            {"name": "infra", "prefix": "secret/infra/"},
            {"name": "apps", "glob": "*/apps/*"},
        ],
        "default_segment": "misc",
    })
    assert len(cfg.rules) == 2
    assert cfg.default_segment == "misc"


def test_segment_config_from_dict_empty():
    cfg = SegmentConfig.from_dict({})
    assert cfg.rules == []
    assert cfg.default_segment == "default"


# ---------------------------------------------------------------------------
# segment_diffs
# ---------------------------------------------------------------------------

def test_segment_diffs_no_rules_all_go_to_default():
    diffs = [_diff("secret/a"), _diff("secret/b", changed=True)]
    report = segment_diffs(diffs)
    assert "default" in report.segments
    assert report.segments["default"].total == 2
    assert report.segments["default"].dirty == 1


def test_segment_diffs_prefix_rule_assigns_correctly():
    config = SegmentConfig(
        rules=[SegmentRule(name="infra", prefix="secret/infra/")]
    )
    diffs = [
        _diff("secret/infra/db", changed=True),
        _diff("secret/app/api"),
    ]
    report = segment_diffs(diffs, config)
    assert report.segments["infra"].total == 1
    assert report.segments["default"].total == 1


def test_segment_diffs_first_matching_rule_wins():
    config = SegmentConfig(rules=[
        SegmentRule(name="first", prefix="secret/"),
        SegmentRule(name="second", prefix="secret/infra/"),
    ])
    diffs = [_diff("secret/infra/db")]
    report = segment_diffs(diffs, config)
    assert "first" in report.segments
    assert "second" not in report.segments


def test_segment_report_to_dict_structure():
    config = SegmentConfig(rules=[SegmentRule(name="apps", glob="*/apps/*")])
    diffs = [_diff("secret/apps/web", changed=True)]
    report = segment_diffs(diffs, config)
    d = report.to_dict()
    assert "total_paths" in d
    assert "segments" in d
    assert d["total_paths"] == 1
    assert d["segments"]["apps"]["dirty"] == 1


def test_segment_report_total_paths_across_buckets():
    config = SegmentConfig(rules=[SegmentRule(name="infra", prefix="infra/")])
    diffs = [_diff("infra/db"), _diff("app/api"), _diff("app/web")]
    report = segment_diffs(diffs, config)
    assert report.total_paths == 3
