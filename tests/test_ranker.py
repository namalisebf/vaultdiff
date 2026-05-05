"""Tests for vaultdiff.ranker."""
from __future__ import annotations

import pytest

from vaultdiff.differ import SecretDiff
from vaultdiff.ranker import RankedPath, _classify_tier, rank_diffs


def _make_diff(
    path: str = "secret/app",
    changed: dict | None = None,
    only_left: dict | None = None,
    only_right: dict | None = None,
) -> SecretDiff:
    return SecretDiff(
        path=path,
        changed_keys=changed or {},
        only_in_left=only_left or {},
        only_in_right=only_right or {},
    )


def test_classify_tier_low():
    assert _classify_tier(0) == "low"
    assert _classify_tier(3.9) == "low"


def test_classify_tier_medium():
    assert _classify_tier(4) == "medium"
    assert _classify_tier(9.9) == "medium"


def test_classify_tier_high():
    assert _classify_tier(10) == "high"
    assert _classify_tier(19.9) == "high"


def test_classify_tier_critical():
    assert _classify_tier(20) == "critical"
    assert _classify_tier(100) == "critical"


def test_rank_diffs_empty():
    assert rank_diffs([]) == []


def test_rank_diffs_no_changes():
    diff = _make_diff()
    results = rank_diffs([diff])
    assert len(results) == 1
    assert results[0].raw_score == 0
    assert results[0].tier == "low"
    assert results[0].weighted_score == 0


def test_rank_diffs_sorted_descending():
    low = _make_diff(path="secret/low")
    high = _make_diff(
        path="secret/high",
        changed={"k": ("a", "b"), "k2": ("c", "d")},
        only_left={"gone": "v"},
        only_right={"new": "v"},
    )
    results = rank_diffs([low, high])
    assert results[0].path == "secret/high"
    assert results[1].path == "secret/low"


def test_ranked_path_to_dict():
    rp = RankedPath(
        path="secret/x",
        raw_score=5.0,
        tier="medium",
        weighted_score=7.5,
        change_summary={"changed": 1, "only_in_left": 0, "only_in_right": 0},
    )
    d = rp.to_dict()
    assert d["path"] == "secret/x"
    assert d["tier"] == "medium"
    assert d["weighted_score"] == 7.5
    assert "change_summary" in d


def test_rank_diffs_change_summary_counts():
    diff = _make_diff(
        path="secret/p",
        changed={"a": ("1", "2")},
        only_left={"b": "v"},
        only_right={"c": "v", "d": "v"},
    )
    result = rank_diffs([diff])[0]
    assert result.change_summary["changed"] == 1
    assert result.change_summary["only_in_left"] == 1
    assert result.change_summary["only_in_right"] == 2
