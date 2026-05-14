"""Tests for vaultdiff.pruner2."""
from __future__ import annotations

import pytest

from vaultdiff.differ import SecretDiff
from vaultdiff.pruner2 import ScorePruneConfig, ScorePruneReport, score_prune


def _diff(path: str, changed=0, only_left=0, only_right=0) -> SecretDiff:
    changed_keys = {f"k{i}": ("old", "new") for i in range(changed)}
    only_in_left = {f"l{i}": "v" for i in range(only_left)}
    only_in_right = {f"r{i}": "v" for i in range(only_right)}
    return SecretDiff(
        path=path,
        changed_keys=changed_keys,
        only_in_left=only_in_left,
        only_in_right=only_in_right,
    )


def test_score_prune_no_config_keeps_all():
    diffs = [_diff("a", changed=1), _diff("b")]
    report = score_prune(diffs)
    assert report.total_kept == 2
    assert report.total_dropped == 0


def test_score_prune_drop_clean_removes_clean_diffs():
    diffs = [_diff("a"), _diff("b", changed=1)]
    config = ScorePruneConfig(drop_clean=True)
    report = score_prune(diffs, config)
    assert report.total_kept == 1
    assert report.kept[0].path == "b"
    assert report.total_dropped == 1
    assert report.dropped[0].path == "a"


def test_score_prune_min_score_filters_low_score():
    diffs = [_diff("a", only_left=1), _diff("b", changed=3)]
    config = ScorePruneConfig(min_score=4.0)
    report = score_prune(diffs, config)
    # "a" scores 1.0 (dropped), "b" scores 6.0 (kept)
    assert report.total_kept == 1
    assert report.kept[0].path == "b"
    assert report.total_dropped == 1


def test_score_prune_max_paths_limits_output():
    diffs = [_diff(f"path/{i}", changed=1) for i in range(5)]
    config = ScorePruneConfig(max_paths=3)
    report = score_prune(diffs, config)
    assert report.total_kept == 3
    assert report.total_dropped == 2


def test_score_prune_max_paths_capped_at_total():
    diffs = [_diff("a", changed=1)]
    config = ScorePruneConfig(max_paths=10)
    report = score_prune(diffs, config)
    assert report.total_kept == 1


def test_score_prune_changed_keys_weighted_double():
    # changed=1 -> score=2.0; only_right=2 -> score=2.0; both equal
    d1 = _diff("a", changed=1)
    d2 = _diff("b", only_right=2)
    config = ScorePruneConfig(min_score=2.0)
    report = score_prune([d1, d2], config)
    assert report.total_kept == 2


def test_score_prune_report_to_dict_keys():
    diffs = [_diff("x", changed=1)]
    report = score_prune(diffs)
    d = report.to_dict()
    assert "total_kept" in d
    assert "total_dropped" in d
    assert "kept_paths" in d
    assert "dropped_paths" in d


def test_score_prune_config_from_dict():
    config = ScorePruneConfig.from_dict({"min_score": 3.5, "drop_clean": True, "max_paths": 5})
    assert config.min_score == 3.5
    assert config.drop_clean is True
    assert config.max_paths == 5


def test_score_prune_config_from_dict_empty():
    config = ScorePruneConfig.from_dict({})
    assert config.min_score == 0.0
    assert config.drop_clean is False
    assert config.max_paths is None
