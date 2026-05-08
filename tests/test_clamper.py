"""Tests for vaultdiff.clamper."""

from vaultdiff.differ import SecretDiff
from vaultdiff.clamper import ClampConfig, ClampReport, clamp_diffs


def _diff(path: str, changed=0, only_left=0, only_right=0) -> SecretDiff:
    return SecretDiff(
        path=path,
        changed={f"k{i}": ("a", "b") for i in range(changed)},
        only_in_left={f"l{i}": "v" for i in range(only_left)},
        only_in_right={f"r{i}": "v" for i in range(only_right)},
    )


def test_clamp_config_defaults():
    cfg = ClampConfig()
    assert cfg.min_changed_keys == 0
    assert cfg.max_changed_keys is None
    assert cfg.min_only_in_left == 0
    assert cfg.max_only_in_left is None
    assert cfg.min_only_in_right == 0
    assert cfg.max_only_in_right is None


def test_clamp_config_from_dict():
    cfg = ClampConfig.from_dict({"min_changed_keys": "2", "max_changed_keys": "5"})
    assert cfg.min_changed_keys == 2
    assert cfg.max_changed_keys == 5


def test_clamp_config_from_dict_empty():
    cfg = ClampConfig.from_dict({})
    assert cfg.min_changed_keys == 0
    assert cfg.max_changed_keys is None


def test_clamp_no_config_keeps_all():
    diffs = [_diff("a", changed=3), _diff("b"), _diff("c", only_left=1)]
    report = clamp_diffs(diffs, ClampConfig())
    assert report.total_kept == 3
    assert report.total_dropped == 0


def test_clamp_max_changed_keys_drops_above_threshold():
    diffs = [_diff("a", changed=1), _diff("b", changed=3), _diff("c", changed=5)]
    report = clamp_diffs(diffs, ClampConfig(max_changed_keys=3))
    assert report.total_kept == 2
    assert "a" in [d.path for d in report.kept]
    assert "b" in [d.path for d in report.kept]
    assert "c" in [d.path for d in report.dropped]


def test_clamp_min_changed_keys_drops_below_threshold():
    diffs = [_diff("a", changed=0), _diff("b", changed=2)]
    report = clamp_diffs(diffs, ClampConfig(min_changed_keys=1))
    assert report.total_kept == 1
    assert report.kept[0].path == "b"
    assert report.dropped[0].path == "a"


def test_clamp_only_in_left_bounds():
    diffs = [_diff("x", only_left=0), _diff("y", only_left=2), _diff("z", only_left=4)]
    report = clamp_diffs(diffs, ClampConfig(min_only_in_left=1, max_only_in_left=3))
    assert report.total_kept == 1
    assert report.kept[0].path == "y"


def test_clamp_only_in_right_bounds():
    diffs = [_diff("p", only_right=1), _diff("q", only_right=10)]
    report = clamp_diffs(diffs, ClampConfig(max_only_in_right=5))
    assert report.total_kept == 1
    assert report.kept[0].path == "p"


def test_clamp_empty_diffs_returns_empty_report():
    report = clamp_diffs([], ClampConfig(min_changed_keys=1))
    assert report.total_kept == 0
    assert report.total_dropped == 0


def test_clamp_report_to_dict_structure():
    diffs = [_diff("a", changed=2), _diff("b")]
    report = clamp_diffs(diffs, ClampConfig(min_changed_keys=1))
    d = report.to_dict()
    assert d["total_kept"] == 1
    assert d["total_dropped"] == 1
    assert "a" in d["kept_paths"]
    assert "b" in d["dropped_paths"]
