"""Unit tests for vaultdiff.comparator."""
from unittest.mock import MagicMock

import pytest

from vaultdiff.comparator import Comparator, ComparisonResult
from vaultdiff.differ import SecretDiff


def _make_diff(changed=None, only_left=None, only_right=None) -> SecretDiff:
    return SecretDiff(
        changed=changed or {},
        only_in_left=only_left or {},
        only_in_right=only_right or {},
    )


def _make_differ(path_diffs: dict) -> MagicMock:
    differ = MagicMock()

    def _diff_secret(path, filter_config=None):
        if path not in path_diffs:
            raise KeyError(f"unknown path: {path}")
        val = path_diffs[path]
        if isinstance(val, Exception):
            raise val
        return val

    differ.diff_secret.side_effect = _diff_secret
    differ.diff_paths.return_value = list(path_diffs.keys())
    return differ


# ------------------------------------------------------------------ #


def test_compare_all_clean():
    differ = _make_differ({
        "secret/a": _make_diff(),
        "secret/b": _make_diff(),
    })
    comp = Comparator(differ)
    result = comp.compare(["secret/a", "secret/b"])

    assert result.passed
    assert not result.has_differences
    assert result.clean_paths == ["secret/a", "secret/b"]
    assert result.changed_paths == []
    assert result.errors == {}


def test_compare_detects_differences():
    differ = _make_differ({
        "secret/a": _make_diff(changed={"key": ("old", "new")}),
        "secret/b": _make_diff(),
    })
    comp = Comparator(differ)
    result = comp.compare(["secret/a", "secret/b"])

    assert not result.passed
    assert result.has_differences
    assert result.changed_paths == ["secret/a"]
    assert result.clean_paths == ["secret/b"]


def test_compare_records_errors():
    differ = _make_differ({
        "secret/ok": _make_diff(),
        "secret/bad": RuntimeError("vault unreachable"),
    })
    comp = Comparator(differ)
    result = comp.compare(["secret/ok", "secret/bad"])

    assert not result.passed
    assert "secret/bad" in result.errors
    assert "vault unreachable" in result.errors["secret/bad"]


def test_compare_recursive_delegates_to_diff_paths():
    differ = _make_differ({
        "secret/env/a": _make_diff(),
        "secret/env/b": _make_diff(only_right={"newkey": "v"}),
    })
    comp = Comparator(differ)
    result = comp.compare_recursive("secret/env")

    differ.diff_paths.assert_called_once_with("secret/env", filter_config=None)
    assert result.has_differences
    assert "secret/env/b" in result.changed_paths


def test_to_dict_structure():
    diff = _make_diff(changed={"x": ("1", "2")})
    differ = _make_differ({"secret/p": diff})
    comp = Comparator(differ)
    result = comp.compare(["secret/p"])
    d = result.to_dict()

    assert d["passed"] is False
    assert d["total_paths"] == 1
    assert "secret/p" in d["changed_paths"]
    assert d["clean_paths"] == []
    assert d["error_paths"] == []


def test_compare_recursive_error_on_list():
    differ = MagicMock()
    differ.diff_paths.side_effect = RuntimeError("permission denied")
    comp = Comparator(differ)
    result = comp.compare_recursive("secret/root")

    assert not result.passed
    assert "secret/root" in result.errors
    assert result.paths == []
