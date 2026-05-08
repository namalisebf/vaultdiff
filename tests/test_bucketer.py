"""Unit tests for vaultdiff.bucketer."""

from __future__ import annotations

import pytest

from vaultdiff.bucketer import Bucket, BucketConfig, BucketRule, bucket_diffs
from vaultdiff.differ import SecretDiff


def _diff(path: str, changed=None, left=None, right=None) -> SecretDiff:
    from vaultdiff.differ import SecretDiff
    d = SecretDiff(path=path)
    d.changed_keys = changed or {}
    d.only_in_left = left or {}
    d.only_in_right = right or {}
    return d


def test_bucket_empty_diffs_returns_empty_report():
    config = BucketConfig()
    report = bucket_diffs([], config)
    assert report.total_paths == 0
    assert report.buckets == {}


def test_bucket_no_rules_all_go_to_default():
    config = BucketConfig(default_bucket="misc")
    diffs = [_diff("secret/a"), _diff("secret/b")]
    report = bucket_diffs(diffs, config)
    assert "misc" in report.buckets
    assert report.buckets["misc"].total == 2


def test_bucket_rule_max_changed_keys_assigns_correctly():
    rules = [
        BucketRule(name="small", max_changed_keys=2),
        BucketRule(name="large", max_changed_keys=10),
    ]
    config = BucketConfig(rules=rules)
    small_diff = _diff("secret/a", changed={"k": ("v1", "v2")})
    large_diff = _diff("secret/b", changed={f"k{i}": ("v1", "v2") for i in range(5)})
    report = bucket_diffs([small_diff, large_diff], config)
    assert "small" in report.buckets
    assert report.buckets["small"].total == 1
    assert report.buckets["small"].diffs[0].path == "secret/a"
    assert "large" in report.buckets
    assert report.buckets["large"].total == 1


def test_bucket_rule_path_prefix_filters_correctly():
    rules = [BucketRule(name="prod", path_prefix="prod/")]
    config = BucketConfig(rules=rules, default_bucket="other")
    prod_diff = _diff("prod/db")
    staging_diff = _diff("staging/db")
    report = bucket_diffs([prod_diff, staging_diff], config)
    assert report.buckets["prod"].total == 1
    assert report.buckets["other"].total == 1


def test_bucket_first_matching_rule_wins():
    rules = [
        BucketRule(name="first", max_changed_keys=5),
        BucketRule(name="second", max_changed_keys=10),
    ]
    config = BucketConfig(rules=rules)
    diff = _diff("secret/x", changed={"k": ("a", "b")})
    report = bucket_diffs([diff], config)
    assert "first" in report.buckets
    assert "second" not in report.buckets


def test_bucket_report_to_dict_structure():
    config = BucketConfig(default_bucket="all")
    diffs = [_diff("secret/a")]
    report = bucket_diffs(diffs, config)
    d = report.to_dict()
    assert "total_paths" in d
    assert "buckets" in d
    assert d["total_paths"] == 1
    assert "all" in d["buckets"]
    assert d["buckets"]["all"]["total"] == 1
    assert "secret/a" in d["buckets"]["all"]["paths"]


def test_bucket_config_from_dict():
    data = {
        "default_bucket": "rest",
        "rules": [
            {"name": "tiny", "max_changed_keys": 1, "path_prefix": "kv/"},
        ],
    }
    config = BucketConfig.from_dict(data)
    assert config.default_bucket == "rest"
    assert len(config.rules) == 1
    assert config.rules[0].name == "tiny"
    assert config.rules[0].max_changed_keys == 1
    assert config.rules[0].path_prefix == "kv/"


def test_bucket_config_from_dict_empty():
    config = BucketConfig.from_dict({})
    assert config.default_bucket == "default"
    assert config.rules == []
