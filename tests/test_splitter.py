"""Tests for vaultdiff.splitter."""
from __future__ import annotations

import pytest

from vaultdiff.differ import SecretDiff
from vaultdiff.splitter import SplitConfig, SplitRule, split_diffs


def _diff(path: str, changed: bool = False) -> SecretDiff:
    left = {"key": "a"}
    right = {"key": "b"} if changed else {"key": "a"}
    return SecretDiff(path=path, left=left, right=right)


def test_split_empty_diffs_returns_empty_report():
    config = SplitConfig()
    report = split_diffs([], config)
    assert report.total() == 0
    assert report.bucket_names() == []


def test_split_no_rules_all_go_to_default():
    config = SplitConfig(default_bucket="catchall")
    diffs = [_diff("secret/app/db"), _diff("secret/app/api")]
    report = split_diffs(diffs, config)
    assert report.bucket_names() == ["catchall"]
    assert len(report.buckets["catchall"]) == 2


def test_split_prefix_rule_assigns_correct_bucket():
    config = SplitConfig(
        rules=[SplitRule(bucket="infra", prefix="secret/infra/")],
        default_bucket="other",
    )
    diffs = [_diff("secret/infra/db"), _diff("secret/app/web")]
    report = split_diffs(diffs, config)
    assert len(report.buckets["infra"]) == 1
    assert report.buckets["infra"][0].path == "secret/infra/db"
    assert len(report.buckets["other"]) == 1


def test_split_glob_rule_matches_pattern():
    config = SplitConfig(
        rules=[SplitRule(bucket="prod", glob="secret/*/prod/*")],
        default_bucket="other",
    )
    diffs = [_diff("secret/app/prod/api"), _diff("secret/app/staging/api")]
    report = split_diffs(diffs, config)
    assert len(report.buckets["prod"]) == 1
    assert report.buckets["prod"][0].path == "secret/app/prod/api"


def test_split_first_matching_rule_wins():
    config = SplitConfig(
        rules=[
            SplitRule(bucket="first", prefix="secret/shared/"),
            SplitRule(bucket="second", glob="secret/shared/*"),
        ],
        default_bucket="other",
    )
    diffs = [_diff("secret/shared/token")]
    report = split_diffs(diffs, config)
    assert "first" in report.buckets
    assert "second" not in report.buckets


def test_split_config_from_dict():
    data = {
        "default_bucket": "misc",
        "rules": [
            {"bucket": "db", "prefix": "secret/db/"},
            {"bucket": "api", "glob": "secret/api/*"},
        ],
    }
    config = SplitConfig.from_dict(data)
    assert config.default_bucket == "misc"
    assert len(config.rules) == 2
    assert config.rules[0].bucket == "db"
    assert config.rules[1].glob == "secret/api/*"


def test_split_to_dict_structure():
    config = SplitConfig(
        rules=[SplitRule(bucket="svc", prefix="secret/svc/")],
        default_bucket="rest",
    )
    diffs = [_diff("secret/svc/auth", changed=True), _diff("secret/other")]
    report = split_diffs(diffs, config)
    d = report.to_dict()
    assert "svc" in d
    assert d["svc"][0]["path"] == "secret/svc/auth"
    assert d["svc"][0]["has_differences"] is True
    assert d["rest"][0]["has_differences"] is False
