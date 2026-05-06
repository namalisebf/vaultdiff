"""Tests for vaultdiff.merger."""
import pytest

from vaultdiff.differ import SecretDiff
from vaultdiff.merger import MergedKey, MergedPath, merge_diffs


def _diff(path: str, left: dict, right: dict) -> SecretDiff:
    changed = {
        k: (left.get(k), right.get(k))
        for k in set(left) | set(right)
        if left.get(k) != right.get(k)
    }
    only_left = {k: v for k, v in left.items() if k not in right}
    only_right = {k: v for k, v in right.items() if k not in left}
    return SecretDiff(
        path=path,
        left=left,
        right=right,
        changed_keys=changed,
        only_in_left=only_left,
        only_in_right=only_right,
    )


def test_merge_empty_input():
    result = merge_diffs({})
    assert result == []


def test_merge_single_env_single_path():
    diffs = {"staging": [_diff("secret/app", {"k": "a"}, {"k": "a"})]}
    result = merge_diffs(diffs)
    assert len(result) == 1
    mp = result[0]
    assert mp.path == "secret/app"
    assert len(mp.keys) == 1
    assert mp.keys[0].key == "k"
    assert mp.keys[0].values == {"staging": "a"}


def test_merge_consistent_key_is_clean():
    diffs = {
        "staging": [_diff("secret/app", {"k": "val"}, {"k": "val"})],
        "prod": [_diff("secret/app", {"k": "val"}, {"k": "val"})],
    }
    result = merge_diffs(diffs)
    assert result[0].is_clean()


def test_merge_inconsistent_key_detected():
    diffs = {
        "staging": [_diff("secret/app", {"db": "localhost"}, {"db": "localhost"})],
        "prod": [_diff("secret/app", {"db": "prod-host"}, {"db": "prod-host"})],
    }
    result = merge_diffs(diffs)
    mp = result[0]
    assert not mp.is_clean()
    bad = mp.inconsistent_keys()
    assert len(bad) == 1
    assert bad[0].key == "db"


def test_merge_multiple_paths_sorted():
    diffs = {
        "staging": [
            _diff("secret/z", {"x": "1"}, {"x": "1"}),
            _diff("secret/a", {"y": "2"}, {"y": "2"}),
        ]
    }
    result = merge_diffs(diffs)
    assert [mp.path for mp in result] == ["secret/a", "secret/z"]


def test_merged_key_to_dict():
    mk = MergedKey(key="token", values={"dev": "abc", "prod": "xyz"})
    d = mk.to_dict()
    assert d["key"] == "token"
    assert d["consistent"] is False
    assert d["values"] == {"dev": "abc", "prod": "xyz"}


def test_merged_path_to_dict_includes_keys():
    mp = MergedPath(
        path="secret/svc",
        keys=[MergedKey(key="port", values={"dev": "8080", "prod": "8080"})],
    )
    d = mp.to_dict()
    assert d["path"] == "secret/svc"
    assert d["clean"] is True
    assert len(d["keys"]) == 1


def test_missing_key_in_one_env_uses_none():
    # staging has key 'extra', prod does not
    diffs = {
        "staging": [_diff("secret/app", {}, {"extra": "only_here"})],
        "prod": [_diff("secret/app", {}, {})],
    }
    result = merge_diffs(diffs)
    mp = result[0]
    extra_key = next(k for k in mp.keys if k.key == "extra")
    assert extra_key.values.get("staging") == "only_here"
    assert "prod" not in extra_key.values or extra_key.values.get("prod") is None
