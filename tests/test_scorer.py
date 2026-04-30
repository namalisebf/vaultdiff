"""Tests for vaultdiff.scorer."""
from vaultdiff.differ import SecretDiff
from vaultdiff.scorer import PathScore, ScoreReport, score_diff, score_diffs


def _make_diff(
    changed=None,
    only_in_left=None,
    only_in_right=None,
) -> SecretDiff:
    return SecretDiff(
        changed_keys=changed or {},
        only_in_left=only_in_left or {},
        only_in_right=only_in_right or {},
    )


def test_score_diff_no_changes():
    diff = _make_diff()
    result = score_diff("secret/app", diff)
    assert isinstance(result, PathScore)
    assert result.score == 0
    assert result.changed_keys == 0
    assert result.only_in_left == 0
    assert result.only_in_right == 0


def test_score_diff_changed_keys_weighted_highest():
    diff = _make_diff(changed={"DB_PASS": ("old", "new")})
    result = score_diff("secret/db", diff)
    assert result.changed_keys == 1
    assert result.score == 3  # 1 * _WEIGHT_CHANGED


def test_score_diff_only_in_left():
    diff = _make_diff(only_in_left={"REMOVED_KEY": "value"})
    result = score_diff("secret/db", diff)
    assert result.only_in_left == 1
    assert result.score == 2  # 1 * _WEIGHT_ONLY_IN_LEFT


def test_score_diff_only_in_right():
    diff = _make_diff(only_in_right={"NEW_KEY": "value"})
    result = score_diff("secret/db", diff)
    assert result.only_in_right == 1
    assert result.score == 1  # 1 * _WEIGHT_ONLY_IN_RIGHT


def test_score_diff_combined():
    diff = _make_diff(
        changed={"A": ("x", "y"), "B": ("1", "2")},
        only_in_left={"C": "gone"},
        only_in_right={"D": "new", "E": "also_new"},
    )
    result = score_diff("secret/mixed", diff)
    # 2*3 + 1*2 + 2*1 = 6 + 2 + 2 = 10
    assert result.score == 10


def test_score_diff_to_dict():
    diff = _make_diff(changed={"KEY": ("a", "b")})
    result = score_diff("secret/app", diff)
    d = result.to_dict()
    assert d["path"] == "secret/app"
    assert d["score"] == 3
    assert d["changed_keys"] == 1


def test_score_diffs_empty():
    report = score_diffs({})
    assert isinstance(report, ScoreReport)
    assert report.total_score == 0
    assert report.path_scores == []


def test_score_diffs_aggregates_total():
    diffs = {
        "secret/a": _make_diff(changed={"X": ("1", "2")}),   # score 3
        "secret/b": _make_diff(only_in_left={"Y": "v"}),      # score 2
        "secret/c": _make_diff(only_in_right={"Z": "v"}),     # score 1
    }
    report = score_diffs(diffs)
    assert report.total_score == 6
    assert len(report.path_scores) == 3


def test_score_report_to_dict():
    diffs = {"secret/x": _make_diff(changed={"K": ("old", "new")})}
    report = score_diffs(diffs)
    d = report.to_dict()
    assert "total_score" in d
    assert "paths" in d
    assert d["total_score"] == 3
    assert d["paths"][0]["path"] == "secret/x"
