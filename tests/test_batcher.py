"""Tests for vaultdiff.batcher."""
from __future__ import annotations

import pytest

from vaultdiff.batcher import Batch, BatchConfig, BatchReport, batch_diffs
from vaultdiff.differ import SecretDiff


def _diff(path: str, changed: int = 0) -> SecretDiff:
    changed_keys = {f"key{i}": ("old", "new") for i in range(changed)}
    return SecretDiff(
        path=path,
        changed_keys=changed_keys,
        only_in_left={},
        only_in_right={},
    )


def test_batch_empty_list_returns_empty_report():
    report = batch_diffs([])
    assert report.total_batches == 0
    assert report.total_paths == 0


def test_batch_single_item_single_batch():
    diffs = [_diff("secret/a")]
    report = batch_diffs(diffs, BatchConfig(size=10))
    assert report.total_batches == 1
    assert report.batches[0].total == 1


def test_batch_splits_into_correct_number_of_batches():
    diffs = [_diff(f"secret/{i}") for i in range(25)]
    report = batch_diffs(diffs, BatchConfig(size=10))
    assert report.total_batches == 3
    assert report.batches[0].total == 10
    assert report.batches[1].total == 10
    assert report.batches[2].total == 5


def test_batch_skip_clean_excludes_no_difference_diffs():
    diffs = [
        _diff("secret/clean", changed=0),
        _diff("secret/dirty", changed=2),
    ]
    report = batch_diffs(diffs, BatchConfig(size=10, skip_clean=True))
    assert report.total_paths == 1
    assert report.batches[0].items[0].path == "secret/dirty"


def test_batch_skip_clean_false_keeps_all():
    diffs = [_diff("secret/a"), _diff("secret/b", changed=1)]
    report = batch_diffs(diffs, BatchConfig(size=10, skip_clean=False))
    assert report.total_paths == 2


def test_batch_dirty_count_correct():
    diffs = [
        _diff("secret/a", changed=0),
        _diff("secret/b", changed=1),
        _diff("secret/c", changed=3),
    ]
    report = batch_diffs(diffs, BatchConfig(size=10))
    assert report.batches[0].dirty_count == 2


def test_batch_to_dict_keys():
    diffs = [_diff("secret/x", changed=1)]
    report = batch_diffs(diffs, BatchConfig(size=5))
    d = report.to_dict()
    assert "total_batches" in d
    assert "total_paths" in d
    assert "batches" in d
    batch_d = d["batches"][0]
    assert "index" in batch_d
    assert "total" in batch_d
    assert "dirty_count" in batch_d
    assert "paths" in batch_d


def test_batch_config_from_dict():
    cfg = BatchConfig.from_dict({"size": "5", "skip_clean": True})
    assert cfg.size == 5
    assert cfg.skip_clean is True


def test_batch_config_from_dict_defaults():
    cfg = BatchConfig.from_dict({})
    assert cfg.size == 10
    assert cfg.skip_clean is False


def test_batch_index_increments():
    diffs = [_diff(f"secret/{i}") for i in range(6)]
    report = batch_diffs(diffs, BatchConfig(size=2))
    indices = [b.index for b in report.batches]
    assert indices == [0, 1, 2]
