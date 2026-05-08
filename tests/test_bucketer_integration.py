"""Integration tests for bucketer: full pipeline from diffs to report."""

from __future__ import annotations

from vaultdiff.bucketer import BucketConfig, BucketRule, bucket_diffs
from vaultdiff.differ import SecretDiff


def _diff(path: str, n_changed: int = 0, n_left: int = 0, n_right: int = 0) -> SecretDiff:
    d = SecretDiff(path=path)
    d.changed_keys = {f"ck{i}": (f"old{i}", f"new{i}") for i in range(n_changed)}
    d.only_in_left = {f"lk{i}": f"lv{i}" for i in range(n_left)}
    d.only_in_right = {f"rk{i}": f"rv{i}" for i in range(n_right)}
    return d


def test_all_clean_diffs_land_in_default():
    config = BucketConfig()
    diffs = [_diff(f"secret/{i}") for i in range(5)]
    report = bucket_diffs(diffs, config)
    assert report.buckets["default"].total == 5
    assert report.total_paths == 5


def test_high_change_diff_skips_small_bucket():
    rules = [
        BucketRule(name="small", max_changed_keys=2),
        BucketRule(name="big", max_changed_keys=20),
    ]
    config = BucketConfig(rules=rules)
    diff = _diff("secret/x", n_changed=10)
    report = bucket_diffs([diff], config)
    assert "big" in report.buckets
    assert "small" not in report.buckets


def test_prefix_rule_separates_environments():
    rules = [
        BucketRule(name="prod", path_prefix="prod/"),
        BucketRule(name="staging", path_prefix="staging/"),
    ]
    config = BucketConfig(rules=rules, default_bucket="other")
    diffs = [
        _diff("prod/db", n_changed=1),
        _diff("staging/db", n_changed=2),
        _diff("dev/db", n_changed=3),
    ]
    report = bucket_diffs(diffs, config)
    assert report.buckets["prod"].total == 1
    assert report.buckets["staging"].total == 1
    assert report.buckets["other"].total == 1


def test_bucket_report_is_dataclass_instance():
    from vaultdiff.bucketer import BucketReport
    config = BucketConfig()
    report = bucket_diffs([_diff("a/b")], config)
    assert isinstance(report, BucketReport)


def test_to_dict_paths_match_diff_paths():
    config = BucketConfig(default_bucket="all")
    diffs = [_diff("kv/alpha"), _diff("kv/beta")]
    report = bucket_diffs(diffs, config)
    d = report.to_dict()
    paths = d["buckets"]["all"]["paths"]
    assert "kv/alpha" in paths
    assert "kv/beta" in paths
