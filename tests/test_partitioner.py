"""Tests for vaultdiff.partitioner."""
import pytest

from vaultdiff.differ import SecretDiff
from vaultdiff.partitioner import (
    PartitionConfig,
    PartitionReport,
    partition_diffs,
    _partition_key,
)


def _diff(path: str, changed: dict | None = None) -> SecretDiff:
    return SecretDiff(
        path=path,
        changed=changed or {},
        only_in_left={},
        only_in_right={},
    )


# --- PartitionConfig ---

def test_partition_config_defaults():
    cfg = PartitionConfig()
    assert cfg.depth == 1
    assert cfg.separator == "/"
    assert cfg.default_partition == "other"


def test_partition_config_from_dict():
    cfg = PartitionConfig.from_dict({"depth": "2", "separator": "/", "default_partition": "misc"})
    assert cfg.depth == 2
    assert cfg.default_partition == "misc"


def test_partition_config_from_dict_empty():
    cfg = PartitionConfig.from_dict({})
    assert cfg.depth == 1


# --- _partition_key ---

def test_partition_key_depth_1():
    assert _partition_key("secret/app/db", 1, "/", "other") == "secret"


def test_partition_key_depth_2():
    assert _partition_key("secret/app/db", 2, "/", "other") == "secret/app"


def test_partition_key_short_path_does_not_exceed():
    assert _partition_key("secret", 3, "/", "other") == "secret"


def test_partition_key_empty_path_returns_default():
    assert _partition_key("", 1, "/", "other") == "other"


# --- partition_diffs ---

def test_partition_empty_list_returns_empty_report():
    report = partition_diffs([])
    assert report.total_partitions == 0
    assert report.partitions == []


def test_partition_groups_by_first_segment():
    diffs = [
        _diff("secret/app/db"),
        _diff("secret/app/cache"),
        _diff("infra/network/vpc"),
    ]
    report = partition_diffs(diffs)
    assert report.total_partitions == 2
    names = [p.name for p in report.partitions]
    assert "infra" in names
    assert "secret" in names


def test_partition_counts_dirty_correctly():
    diffs = [
        _diff("secret/app/db", changed={"password": ("old", "new")}),
        _diff("secret/app/cache"),
    ]
    report = partition_diffs(diffs)
    assert report.total_partitions == 1
    p = report.partitions[0]
    assert p.total == 2
    assert p.dirty == 1


def test_partition_sorted_alphabetically():
    diffs = [_diff("z/path"), _diff("a/path"), _diff("m/path")]
    report = partition_diffs(diffs)
    names = [p.name for p in report.partitions]
    assert names == sorted(names)


def test_partition_to_dict_structure():
    diffs = [_diff("secret/app", changed={"k": ("a", "b")})]
    report = partition_diffs(diffs)
    d = report.to_dict()
    assert "total_partitions" in d
    assert "partitions" in d
    assert d["partitions"][0]["dirty"] == 1
    assert d["partitions"][0]["clean"] == 0


def test_partition_custom_depth():
    cfg = PartitionConfig(depth=2)
    diffs = [
        _diff("secret/app/db"),
        _diff("secret/app/cache"),
        _diff("secret/infra/vpc"),
    ]
    report = partition_diffs(diffs, config=cfg)
    assert report.total_partitions == 2
    names = {p.name for p in report.partitions}
    assert "secret/app" in names
    assert "secret/infra" in names
