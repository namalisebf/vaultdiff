"""Unit tests for vaultdiff.digester."""
from __future__ import annotations

import pytest

from vaultdiff.differ import SecretDiff
from vaultdiff.digester import (
    DigestEntry,
    DigestReport,
    _digest_secret,
    digest_diffs,
)


def _diff(path: str, left: dict, right: dict) -> SecretDiff:
    sd = SecretDiff(path=path, left_data=left, right_data=right)
    return sd


def test_digest_secret_deterministic():
    data = {"key": "value", "other": "123"}
    assert _digest_secret(data) == _digest_secret(data)


def test_digest_secret_order_independent():
    a = {"x": "1", "y": "2"}
    b = {"y": "2", "x": "1"}
    assert _digest_secret(a) == _digest_secret(b)


def test_digest_secret_differs_on_value_change():
    a = {"key": "value"}
    b = {"key": "other"}
    assert _digest_secret(a) != _digest_secret(b)


def test_digest_secret_differs_on_key_change():
    """Changing a key name (not just value) should produce a different digest."""
    a = {"key1": "value"}
    b = {"key2": "value"}
    assert _digest_secret(a) != _digest_secret(b)


def test_digest_entry_match_true_when_same():
    d = _digest_secret({"k": "v"})
    entry = DigestEntry(path="sec/a", left_digest=d, right_digest=d)
    assert entry.match is True


def test_digest_entry_match_false_when_different():
    entry = DigestEntry(path="sec/a", left_digest="aaa", right_digest="bbb")
    assert entry.match is False


def test_digest_entry_to_dict_keys():
    entry = DigestEntry(path="sec/a", left_digest="aaa", right_digest="aaa")
    d = entry.to_dict()
    assert set(d.keys()) == {"path", "left_digest", "right_digest", "match"}


def test_digest_diffs_all_match():
    data = {"password": "secret"}
    diffs = [_diff("sec/a", data, data)]
    report = digest_diffs(diffs)
    assert report.all_match is True
    assert report.mismatched_paths == []


def test_digest_diffs_detects_mismatch():
    diffs = [
        _diff("sec/a", {"k": "v1"}, {"k": "v2"}),
        _diff("sec/b", {"k": "same"}, {"k": "same"}),
    ]
    report = digest_diffs(diffs)
    assert report.all_match is False
    assert "sec/a" in report.mismatched_paths
    assert "sec/b" not in report.mismatched_paths


def test_digest_diffs_none_data_produces_none_digest():
    diff = SecretDiff(path="sec/missing", left_data=None, right_data={"k": "v"})
    report = digest_diffs([diff])
    entry = report.entries[0]
    assert entry.left_digest is None
    assert entry.right_digest is not None
    assert entry.match is False


def test_digest_diffs_both_none_data_produces_none_digests():
    """When both sides are None the entry should have no digests and not match."""
    diff = SecretDiff(path="sec/gone", left_data=None, right_data=None)
    report = digest_diffs([diff])
    entry = report.entries[0]
    assert entry.left_digest is None
    assert entry.right_digest is None
    assert entry.match is False


def test_digest_report_to_dict_structure():
    diffs = [_diff("sec/x", {"a": "1"}, {"a": "1"})]
    report = digest_diffs(diffs)
    d = report.to_dict()
    assert "all_match" in d
    assert "mismatched_paths" in d
    assert "entries" in d
    assert isinstance(d["entries"], list)
