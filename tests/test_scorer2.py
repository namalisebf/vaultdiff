"""Tests for vaultdiff.scorer2."""
from __future__ import annotations

from vaultdiff.differ import SecretDiff
from vaultdiff.scorer2 import (
    WeightedScoreConfig,
    score_diffs_weighted,
)


def _diff(
    path: str = "secret/app",
    changed: dict | None = None,
    left: dict | None = None,
    right: dict | None = None,
) -> SecretDiff:
    return SecretDiff(
        path=path,
        changed_keys=changed or {},
        only_in_left=left or {},
        only_in_right=right or {},
    )


def test_score_clean_diff_is_zero():
    report = score_diffs_weighted([_diff()])
    assert len(report.entries) == 1
    assert report.entries[0].score == 0.0
    assert report.total_score == 0.0


def test_score_changed_keys_use_weight():
    d = _diff(changed={"k": ("a", "b")})
    report = score_diffs_weighted([d])
    assert report.entries[0].score == 3.0


def test_score_only_in_left_uses_weight():
    d = _diff(left={"k": "v"})
    report = score_diffs_weighted([d])
    assert report.entries[0].score == 1.0


def test_score_only_in_right_uses_weight():
    d = _diff(right={"k": "v"})
    report = score_diffs_weighted([d])
    assert report.entries[0].score == 1.0


def test_custom_weights_applied():
    config = WeightedScoreConfig(weights={"changed": 10.0, "only_in_left": 2.0, "only_in_right": 0.5})
    d = _diff(changed={"a": ("x", "y")}, left={"b": "v"}, right={"c": "w"})
    report = score_diffs_weighted([d], config)
    expected = 10.0 + 2.0 + 0.5
    assert report.entries[0].score == expected


def test_entries_sorted_by_score_descending():
    d1 = _diff(path="a", changed={"x": ("1", "2")})
    d2 = _diff(path="b")
    d3 = _diff(path="c", changed={"x": ("1", "2"), "y": ("3", "4")})
    report = score_diffs_weighted([d1, d2, d3])
    scores = [e.score for e in report.entries]
    assert scores == sorted(scores, reverse=True)
    assert report.entries[0].path == "c"


def test_total_score_is_sum():
    d1 = _diff(path="a", changed={"k": ("a", "b")})
    d2 = _diff(path="b", right={"k": "v"})
    report = score_diffs_weighted([d1, d2])
    assert report.total_score == 3.0 + 1.0


def test_to_dict_structure():
    d = _diff(changed={"k": ("a", "b")})
    report = score_diffs_weighted([d])
    result = report.to_dict()
    assert "total_score" in result
    assert "entries" in result
    entry = result["entries"][0]
    assert set(entry.keys()) == {"path", "changed_keys", "only_in_left", "only_in_right", "score"}


def test_config_from_dict_merges_defaults():
    config = WeightedScoreConfig.from_dict({"weights": {"changed": 5.0}})
    assert config.weights["changed"] == 5.0
    assert config.weights["only_in_left"] == 1.0
    assert config.weights["only_in_right"] == 1.0


def test_empty_list_returns_empty_report():
    report = score_diffs_weighted([])
    assert report.entries == []
    assert report.total_score == 0.0
