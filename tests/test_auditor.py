"""Tests for vaultdiff.auditor."""

import json
import pytest
from pathlib import Path
from unittest.mock import MagicMock

from vaultdiff.auditor import Auditor, AuditEntry
from vaultdiff.differ import SecretDiff


def _make_diff(changed=None, only_left=None, only_right=None) -> SecretDiff:
    diff = MagicMock(spec=SecretDiff)
    diff.changed = [(k, v) for k, v in (changed or {}).items()]
    diff.only_in_left = only_left or {}
    diff.only_in_right = only_right or {}
    diff.has_differences.return_value = bool(changed or only_left or only_right)
    return diff


def test_record_no_differences():
    auditor = Auditor(left_addr="http://vault-a", right_addr="http://vault-b")
    diff = _make_diff()
    entry = auditor.record("secret/app/config", diff)
    assert isinstance(entry, AuditEntry)
    assert entry.path == "secret/app/config"
    assert entry.has_differences is False
    assert entry.changed_keys == []
    assert entry.only_in_left == []
    assert entry.only_in_right == []


def test_record_with_changed_keys():
    auditor = Auditor(left_addr="http://vault-a", right_addr="http://vault-b")
    diff = _make_diff(changed={"DB_PASS": ("old", "new")})
    entry = auditor.record("secret/db", diff)
    assert entry.has_differences is True
    assert "DB_PASS" in entry.changed_keys


def test_record_only_in_left():
    auditor = Auditor(left_addr="http://vault-a", right_addr="http://vault-b")
    diff = _make_diff(only_left={"LEGACY_KEY": "val"})
    entry = auditor.record("secret/legacy", diff)
    assert "LEGACY_KEY" in entry.only_in_left
    assert entry.only_in_right == []


def test_record_only_in_right():
    auditor = Auditor(left_addr="http://vault-a", right_addr="http://vault-b")
    diff = _make_diff(only_right={"NEW_KEY": "val"})
    entry = auditor.record("secret/new", diff)
    assert "NEW_KEY" in entry.only_in_right


def test_entries_accumulate():
    auditor = Auditor(left_addr="http://vault-a", right_addr="http://vault-b")
    auditor.record("secret/a", _make_diff())
    auditor.record("secret/b", _make_diff(changed={"X": ("1", "2")}))
    assert len(auditor.entries()) == 2


def test_summary():
    auditor = Auditor(left_addr="http://vault-a", right_addr="http://vault-b")
    auditor.record("secret/a", _make_diff())
    auditor.record("secret/b", _make_diff(changed={"X": ("1", "2")}))
    auditor.record("secret/c", _make_diff())
    s = auditor.summary()
    assert s["total_paths"] == 3
    assert s["paths_with_differences"] == 1
    assert s["clean_paths"] == 2


def test_write_creates_ndjson(tmp_path):
    out_file = tmp_path / "audit.ndjson"
    auditor = Auditor(
        left_addr="http://vault-a",
        right_addr="http://vault-b",
        output_path=str(out_file),
    )
    auditor.record("secret/a", _make_diff())
    auditor.record("secret/b", _make_diff(changed={"KEY": ("v1", "v2")}))
    auditor.write()
    lines = out_file.read_text().strip().splitlines()
    assert len(lines) == 2
    first = json.loads(lines[0])
    assert first["path"] == "secret/a"
    assert "timestamp" in first


def test_write_raises_without_output_path():
    auditor = Auditor(left_addr="http://vault-a", right_addr="http://vault-b")
    auditor.record("secret/x", _make_diff())
    with pytest.raises(ValueError, match="No output_path"):
        auditor.write()


def test_entry_to_dict_contains_all_fields():
    auditor = Auditor(left_addr="http://vault-a", right_addr="http://vault-b")
    entry = auditor.record("secret/x", _make_diff(changed={"A": ("1", "2")}))
    d = entry.to_dict()
    for key in ("timestamp", "path", "left_addr", "right_addr",
                "changed_keys", "only_in_left", "only_in_right", "has_differences"):
        assert key in d
