"""Unit tests for vaultdiff.correlator."""
from __future__ import annotations

from vaultdiff.correlator import CorrelatedKey, correlate_diffs
from vaultdiff.differ import SecretDiff


def _diff(path: str, changed=None, only_left=None, only_right=None) -> SecretDiff:
    changed = changed or {}
    only_left = only_left or {}
    only_right = only_right or {}
    return SecretDiff(
        path=path,
        changed_keys=changed,
        only_in_left=only_left,
        only_in_right=only_right,
    )


def test_correlate_empty_input():
    report = correlate_diffs({})
    assert report.total_paths == 0
    assert report.paths_with_universal_changes == []


def test_correlate_single_env_single_change():
    diffs = [_diff("secret/app", changed={"KEY": ("old", "new")})]
    report = correlate_diffs({"staging": diffs})
    assert report.total_paths == 1
    cp = report.paths[0]
    assert cp.path == "secret/app"
    assert len(cp.keys) == 1
    ck = cp.keys[0]
    assert ck.key == "KEY"
    assert ck.environments_changed == ["staging"]
    assert ck.environments_clean == []
    assert ck.is_universal_change is True


def test_correlate_two_envs_both_changed():
    diffs_a = [_diff("secret/app", changed={"DB_PASS": ("x", "y")})]
    diffs_b = [_diff("secret/app", changed={"DB_PASS": ("a", "b")})]
    report = correlate_diffs({"prod": diffs_a, "staging": diffs_b})
    assert report.total_paths == 1
    ck = report.paths[0].keys[0]
    assert set(ck.environments_changed) == {"prod", "staging"}
    assert ck.environments_clean == []
    assert ck.is_universal_change is True


def test_correlate_two_envs_partial_change():
    diffs_a = [_diff("secret/app", changed={"API_KEY": ("old", "new")})]
    diffs_b = [_diff("secret/app")]  # no changes in staging
    report = correlate_diffs({"prod": diffs_a, "staging": diffs_b})
    cp = report.paths[0]
    ck = cp.keys[0]
    assert ck.environments_changed == ["prod"]
    assert "staging" in ck.environments_clean
    assert ck.is_universal_change is False
    assert cp.partial_change_keys == [ck]
    assert cp.universal_change_keys == []


def test_correlate_only_in_left_and_right_counted():
    diffs = [_diff("secret/db", only_left={"OLD": "v"}, only_right={"NEW": "v"})]
    report = correlate_diffs({"env1": diffs})
    cp = report.paths[0]
    keys = {ck.key for ck in cp.keys}
    assert "OLD" in keys
    assert "NEW" in keys


def test_correlate_paths_sorted():
    diffs = [
        _diff("secret/z", changed={"K": ("a", "b")}),
        _diff("secret/a", changed={"K": ("a", "b")}),
    ]
    report = correlate_diffs({"env": diffs})
    paths = [cp.path for cp in report.paths]
    assert paths == sorted(paths)


def test_to_dict_structure():
    diffs = [_diff("secret/app", changed={"TOKEN": ("old", "new")})]
    report = correlate_diffs({"prod": diffs})
    d = report.to_dict()
    assert "total_paths" in d
    assert "paths_with_universal_changes" in d
    assert "paths" in d
    assert "keys" in d["paths"][0]
    key_dict = d["paths"][0]["keys"][0]
    assert "key" in key_dict
    assert "environments_changed" in key_dict
    assert "is_universal_change" in key_dict


def test_paths_with_universal_changes_filter():
    diffs_a = [_diff("secret/x", changed={"K": ("a", "b")})]
    diffs_b = [_diff("secret/x")]  # no changes
    report = correlate_diffs({"e1": diffs_a, "e2": diffs_b})
    # K only changed in e1, not universal
    assert report.paths_with_universal_changes == []


def test_change_count_property():
    ck = CorrelatedKey(key="X", environments_changed=["a", "b"], environments_clean=["c"])
    assert ck.change_count == 2
