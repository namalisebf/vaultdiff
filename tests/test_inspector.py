"""Tests for vaultdiff.inspector."""
from __future__ import annotations

import math
import pytest

from vaultdiff.differ import SecretDiff
from vaultdiff.inspector import (
    _shannon_entropy,
    _value_type,
    inspect_diff,
    inspect_diffs,
    KeyInspection,
    PathInspection,
)


def _diff(
    path="secret/app",
    left=None,
    right=None,
    changed=None,
    only_left=None,
    only_right=None,
) -> SecretDiff:
    return SecretDiff(
        path=path,
        left_data=left or {},
        right_data=right or {},
        changed_keys=changed or [],
        only_in_left=only_left or [],
        only_in_right=only_right or [],
    )


def test_shannon_entropy_empty():
    assert _shannon_entropy("") == 0.0


def test_shannon_entropy_uniform():
    # "aaaa" has entropy 0
    assert _shannon_entropy("aaaa") == pytest.approx(0.0)


def test_shannon_entropy_two_symbols():
    # "ab" → entropy = 1.0 bit
    assert _shannon_entropy("ab") == pytest.approx(1.0)


def test_value_type_empty():
    assert _value_type("") == "empty"


def test_value_type_numeric():
    assert _value_type("12345") == "numeric"


def test_value_type_hex():
    assert _value_type("deadbeef") == "hex"


def test_value_type_string():
    assert _value_type("hello world!") == "string"


def test_inspect_diff_no_differences():
    d = _diff()
    result = inspect_diff(d)
    assert isinstance(result, PathInspection)
    assert result.path == "secret/app"
    assert result.keys == []


def test_inspect_diff_changed_key():
    d = _diff(
        left={"token": "abc"},
        right={"token": "xyz"},
        changed=["token"],
    )
    result = inspect_diff(d)
    assert len(result.keys) == 1
    ki = result.keys[0]
    assert ki.key == "token"
    assert ki.present_in_left is True
    assert ki.present_in_right is True
    assert ki.left_length == 3
    assert ki.right_length == 3


def test_inspect_diff_only_in_left():
    d = _diff(left={"gone": "val"}, only_left=["gone"])
    ki = inspect_diff(d).keys[0]
    assert ki.present_in_left is True
    assert ki.present_in_right is False
    assert ki.right_length is None
    assert ki.right_entropy is None
    assert ki.right_type is None


def test_inspect_diff_only_in_right():
    d = _diff(right={"new": "secret"}, only_right=["new"])
    ki = inspect_diff(d).keys[0]
    assert ki.present_in_left is False
    assert ki.present_in_right is True


def test_inspect_diff_to_dict_structure():
    d = _diff(left={"k": "v"}, right={"k": "w"}, changed=["k"])
    result = inspect_diff(d).to_dict()
    assert "path" in result
    assert "keys" in result
    ki_dict = result["keys"][0]
    expected_fields = {
        "key", "present_in_left", "present_in_right",
        "left_length", "right_length",
        "left_entropy", "right_entropy",
        "left_type", "right_type",
    }
    assert set(ki_dict.keys()) == expected_fields


def test_inspect_diffs_multiple_paths():
    diffs = [
        _diff(path="a", left={"x": "1"}, only_left=["x"]),
        _diff(path="b"),
    ]
    results = inspect_diffs(diffs)
    assert len(results) == 2
    assert results[0].path == "a"
    assert results[1].path == "b"
