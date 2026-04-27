"""Tests for vaultdiff.snapshot module."""

from __future__ import annotations

import json
import os
import tempfile

import pytest

from vaultdiff.snapshot import (
    Snapshot,
    SnapshotEntry,
    diff_snapshots,
    load_snapshot,
    save_snapshot,
)


def _make_snapshot(label: str, entries: list) -> Snapshot:
    return Snapshot(label=label, entries=[SnapshotEntry(path=p, keys=k) for p, k in entries])


def test_snapshot_entry_to_dict():
    entry = SnapshotEntry(path="secret/app", keys=["db_pass", "api_key"])
    d = entry.to_dict()
    assert d["path"] == "secret/app"
    assert d["keys"] == ["api_key", "db_pass"]  # sorted
    assert "captured_at" in d


def test_snapshot_entry_roundtrip():
    entry = SnapshotEntry(path="secret/svc", keys=["token"])
    restored = SnapshotEntry.from_dict(entry.to_dict())
    assert restored.path == entry.path
    assert restored.keys == entry.keys


def test_snapshot_to_dict_and_from_dict():
    snap = _make_snapshot("prod", [("secret/a", ["x"]), ("secret/b", ["y"])])
    restored = Snapshot.from_dict(snap.to_dict())
    assert restored.label == "prod"
    assert len(restored.entries) == 2
    assert restored.entries[0].path == "secret/a"


def test_save_and_load_snapshot(tmp_path):
    snap = _make_snapshot("staging", [("secret/cfg", ["key1", "key2"])])
    filepath = str(tmp_path / "snap.json")
    save_snapshot(snap, filepath)
    loaded = load_snapshot(filepath)
    assert loaded.label == "staging"
    assert loaded.entries[0].keys == ["key1", "key2"]


def test_load_snapshot_missing_file():
    with pytest.raises(FileNotFoundError):
        load_snapshot("/nonexistent/path/snap.json")


def test_diff_snapshots_no_changes():
    snap = _make_snapshot("v1", [("secret/a", ["x"])])
    result = diff_snapshots(snap, snap)
    assert result == {}


def test_diff_snapshots_added_path():
    old = _make_snapshot("v1", [("secret/a", ["x"])])
    new = _make_snapshot("v2", [("secret/a", ["x"]), ("secret/b", ["y"])])
    result = diff_snapshots(old, new)
    assert "secret/b" in result
    assert result["secret/b"]["status"] == "added"
    assert result["secret/b"]["keys_added"] == ["y"]


def test_diff_snapshots_removed_path():
    old = _make_snapshot("v1", [("secret/a", ["x"]), ("secret/b", ["y"])])
    new = _make_snapshot("v2", [("secret/a", ["x"])])
    result = diff_snapshots(old, new)
    assert "secret/b" in result
    assert result["secret/b"]["status"] == "removed"
    assert result["secret/b"]["keys_removed"] == ["y"]


def test_diff_snapshots_changed_keys():
    old = _make_snapshot("v1", [("secret/a", ["x", "z"])])
    new = _make_snapshot("v2", [("secret/a", ["x", "w"])])
    result = diff_snapshots(old, new)
    assert "secret/a" in result
    assert result["secret/a"]["status"] == "changed"
    assert result["secret/a"]["keys_added"] == ["w"]
    assert result["secret/a"]["keys_removed"] == ["z"]


def test_diff_snapshots_unchanged_path_not_in_result():
    old = _make_snapshot("v1", [("secret/a", ["x"]), ("secret/b", ["y"])])
    new = _make_snapshot("v2", [("secret/a", ["x"]), ("secret/b", ["y"])])
    result = diff_snapshots(old, new)
    assert result == {}
