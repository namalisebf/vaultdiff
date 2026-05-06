"""Tests for vaultdiff.pruner."""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from vaultdiff.differ import SecretDiff
from vaultdiff.pruner import PruneConfig, PruneReport, prune_diffs


def _diff(path: str, *, has_diff: bool = False) -> SecretDiff:
    d = MagicMock(spec=SecretDiff)
    d.path = path
    d.has_differences = has_diff
    return d


# ---------------------------------------------------------------------------
# PruneConfig.from_dict
# ---------------------------------------------------------------------------

def test_prune_config_from_dict_defaults():
    cfg = PruneConfig.from_dict({})
    assert cfg.drop_clean is False
    assert cfg.exclude_patterns == []
    assert cfg.max_paths is None


def test_prune_config_from_dict_values():
    cfg = PruneConfig.from_dict({"drop_clean": True, "exclude_patterns": ["tmp/*"], "max_paths": 5})
    assert cfg.drop_clean is True
    assert cfg.exclude_patterns == ["tmp/*"]
    assert cfg.max_paths == 5


# ---------------------------------------------------------------------------
# prune_diffs — drop_clean
# ---------------------------------------------------------------------------

def test_prune_keeps_all_when_no_config():
    diffs = [_diff("a"), _diff("b", has_diff=True)]
    report = prune_diffs(diffs, PruneConfig())
    assert len(report.kept) == 2
    assert report.total_dropped == 0


def test_prune_drop_clean_removes_no_difference_paths():
    diffs = [_diff("clean"), _diff("dirty", has_diff=True)]
    report = prune_diffs(diffs, PruneConfig(drop_clean=True))
    assert [d.path for d in report.kept] == ["dirty"]
    assert [d.path for d in report.dropped] == ["clean"]


# ---------------------------------------------------------------------------
# prune_diffs — exclude_patterns
# ---------------------------------------------------------------------------

def test_prune_exclude_pattern_glob():
    diffs = [_diff("secret/prod/db"), _diff("secret/dev/db"), _diff("secret/prod/api")]
    report = prune_diffs(diffs, PruneConfig(exclude_patterns=["secret/dev/*"]))
    assert [d.path for d in report.kept] == ["secret/prod/db", "secret/prod/api"]
    assert report.total_dropped == 1


def test_prune_exclude_multiple_patterns():
    diffs = [_diff("a/b"), _diff("c/d"), _diff("e/f")]
    report = prune_diffs(diffs, PruneConfig(exclude_patterns=["a/*", "e/*"]))
    assert [d.path for d in report.kept] == ["c/d"]


# ---------------------------------------------------------------------------
# prune_diffs — max_paths
# ---------------------------------------------------------------------------

def test_prune_max_paths_limits_kept():
    diffs = [_diff(f"path/{i}", has_diff=True) for i in range(5)]
    report = prune_diffs(diffs, PruneConfig(max_paths=3))
    assert len(report.kept) == 3
    assert report.total_dropped == 2


def test_prune_max_paths_larger_than_total_keeps_all():
    diffs = [_diff("x"), _diff("y")]
    report = prune_diffs(diffs, PruneConfig(max_paths=10))
    assert len(report.kept) == 2
    assert report.total_dropped == 0


# ---------------------------------------------------------------------------
# PruneReport.to_dict
# ---------------------------------------------------------------------------

def test_prune_report_to_dict():
    kept = [_diff("k1"), _diff("k2")]
    dropped = [_diff("d1")]
    report = PruneReport(kept=kept, dropped=dropped)
    result = report.to_dict()
    assert result["kept"] == ["k1", "k2"]
    assert result["dropped"] == ["d1"]
    assert result["total_dropped"] == 1
