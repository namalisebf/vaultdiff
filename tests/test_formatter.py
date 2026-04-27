"""Tests for vaultdiff.formatter."""

import pytest
from vaultdiff.differ import SecretDiff
from vaultdiff.formatter import format_diff_text, format_diff_json


PATH = "secret/myapp"


def _changed(key, left, right):
    return SecretDiff(key=key, left_value=left, right_value=right,
                      only_in_left=False, only_in_right=False)


def _removed(key, left):
    return SecretDiff(key=key, left_value=left, right_value=None,
                      only_in_left=True, only_in_right=False)


def _added(key, right):
    return SecretDiff(key=key, left_value=None, right_value=right,
                      only_in_left=False, only_in_right=True)


def test_format_text_no_differences():
    result = format_diff_text(PATH, [], color=False)
    assert "(no differences)" in result
    assert PATH in result


def test_format_text_removed_key():
    result = format_diff_text(PATH, [_removed("db_pass", "secret")], color=False)
    assert "-" in result
    assert "db_pass" in result
    assert "'secret'" in result


def test_format_text_added_key():
    result = format_diff_text(PATH, [_added("new_key", "val")], color=False)
    assert "+" in result
    assert "new_key" in result


def test_format_text_changed_key():
    result = format_diff_text(PATH, [_changed("api_key", "old", "new")], color=False)
    assert "~" in result
    assert "api_key" in result
    assert "'old'" in result
    assert "'new'" in result


def test_format_text_keys_sorted():
    diffs = [_removed("z_key", "v"), _added("a_key", "v")]
    result = format_diff_text(PATH, diffs, color=False)
    assert result.index("a_key") < result.index("z_key")


def test_format_json_no_differences():
    result = format_diff_json(PATH, [])
    assert result["path"] == PATH
    assert result["total"] == 0
    assert result["differences"] == []


def test_format_json_change_types():
    diffs = [
        _changed("k1", "old", "new"),
        _removed("k2", "gone"),
        _added("k3", "fresh"),
    ]
    result = format_diff_json(PATH, diffs)
    assert result["total"] == 3
    by_key = {e["key"]: e for e in result["differences"]}
    assert by_key["k1"]["change"] == "changed"
    assert by_key["k2"]["change"] == "removed"
    assert by_key["k3"]["change"] == "added"


def test_format_json_left_right_values():
    diffs = [_changed("token", "abc", "xyz")]
    result = format_diff_json(PATH, diffs)
    entry = result["differences"][0]
    assert entry["left"] == "abc"
    assert entry["right"] == "xyz"
