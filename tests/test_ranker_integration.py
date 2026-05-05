"""Integration tests for ranker — exercises scorer + ranker together."""
from __future__ import annotations

from vaultdiff.differ import SecretDiff
from vaultdiff.ranker import rank_diffs, RankedPath


def _diff(
    path: str,
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


def test_all_clean_paths_score_zero():
    diffs = [_diff(f"secret/p{i}") for i in range(4)]
    results = rank_diffs(diffs)
    assert all(r.raw_score == 0 for r in results)
    assert all(r.tier == "low" for r in results)


def test_high_change_path_ranks_first():
    low = _diff("secret/low")
    busy = _diff(
        "secret/busy",
        changed={f"k{i}": ("old", "new") for i in range(5)},
        only_left={f"gone{i}": "v" for i in range(3)},
        only_right={f"new{i}": "v" for i in range(3)},
    )
    results = rank_diffs([low, busy])
    assert results[0].path == "secret/busy"


def test_weighted_score_exceeds_raw_for_non_low_tier():
    diff = _diff(
        "secret/x",
        changed={f"k{i}": ("a", "b") for i in range(3)},
    )
    results = rank_diffs([diff])
    r = results[0]
    assert r.weighted_score >= r.raw_score


def test_ranked_path_is_dataclass_instance():
    diff = _diff("secret/z", changed={"key": ("v1", "v2")})
    results = rank_diffs([diff])
    assert isinstance(results[0], RankedPath)


def test_to_dict_contains_expected_keys():
    diff = _diff("secret/d", only_right={"added": "val"})
    d = rank_diffs([diff])[0].to_dict()
    for key in ("path", "raw_score", "tier", "weighted_score", "change_summary"):
        assert key in d


def test_change_summary_reflects_diff():
    diff = _diff(
        "secret/s",
        changed={"a": ("1", "2"), "b": ("3", "4")},
        only_left={"c": "v"},
        only_right={"d": "v", "e": "v"},
    )
    summary = rank_diffs([diff])[0].change_summary
    assert summary["changed"] == 2
    assert summary["only_in_left"] == 1
    assert summary["only_in_right"] == 2
