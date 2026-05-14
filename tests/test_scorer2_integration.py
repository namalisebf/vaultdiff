"""Integration tests for scorer2: scorer + config interact correctly end-to-end."""
from __future__ import annotations

from vaultdiff.differ import SecretDiff
from vaultdiff.scorer2 import WeightedScoreConfig, score_diffs_weighted


def _diff(path: str, changed: int = 0, left: int = 0, right: int = 0) -> SecretDiff:
    return SecretDiff(
        path=path,
        changed_keys={f"ck{i}": ("a", "b") for i in range(changed)},
        only_in_left={f"lk{i}": "v" for i in range(left)},
        only_in_right={f"rk{i}": "v" for i in range(right)},
    )


def test_high_change_path_ranks_first():
    diffs = [
        _diff("low", changed=1),
        _diff("high", changed=5),
        _diff("zero"),
    ]
    report = score_diffs_weighted(diffs)
    assert report.entries[0].path == "high"
    assert report.entries[-1].path == "zero"


def test_custom_weights_change_ranking():
    diffs = [
        _diff("many-left", left=10),
        _diff("one-changed", changed=1),
    ]
    # With high weight on left-only, many-left should win
    config = WeightedScoreConfig(weights={"changed": 1.0, "only_in_left": 5.0, "only_in_right": 1.0})
    report = score_diffs_weighted(diffs, config)
    assert report.entries[0].path == "many-left"


def test_score_report_total_matches_sum_of_entries():
    diffs = [_diff(f"p{i}", changed=i) for i in range(5)]
    report = score_diffs_weighted(diffs)
    assert report.total_score == sum(e.score for e in report.entries)


def test_scored_entry_to_dict_is_serialisable():
    import json
    diffs = [_diff("secret/app", changed=2, left=1, right=1)]
    report = score_diffs_weighted(diffs)
    serialised = json.dumps(report.to_dict())
    data = json.loads(serialised)
    assert data["entries"][0]["path"] == "secret/app"


def test_from_dict_empty_uses_defaults():
    config = WeightedScoreConfig.from_dict({})
    assert config.weights["changed"] == 3.0
    assert config.weights["only_in_left"] == 1.0
    assert config.weights["only_in_right"] == 1.0
