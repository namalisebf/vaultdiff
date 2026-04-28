"""Tests for vaultdiff.drift module."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from click.testing import CliRunner

from vaultdiff.drift import DriftEntry, detect_drift
from vaultdiff.snapshot import Snapshot, SnapshotEntry


def _make_snapshot(entries):
    snap = Snapshot(entries=[])
    for path, data in entries.items():
        snap.entries.append(SnapshotEntry(path=path, data=data))
    return snap


def _make_differ(live_data: dict):
    """Return a VaultDiffer-like object whose right_client returns live_data per path."""
    differ = MagicMock()
    differ.right_client.read_secret.side_effect = lambda path, mount="secret": live_data.get(path, {})
    return differ


def test_no_drift_when_data_matches():
    snapshot = _make_snapshot({"app/config": {"key": "value"}})
    differ = _make_differ({"app/config": {"key": "value"}})
    entries = detect_drift(snapshot, differ)
    assert len(entries) == 1
    assert not entries[0].has_drift


def test_detects_changed_key():
    snapshot = _make_snapshot({"app/config": {"key": "old"}})
    differ = _make_differ({"app/config": {"key": "new"}})
    entries = detect_drift(snapshot, differ)
    assert entries[0].changed_keys == ["key"]
    assert entries[0].has_drift


def test_detects_added_key():
    snapshot = _make_snapshot({"app/config": {"key": "val"}})
    differ = _make_differ({"app/config": {"key": "val", "new_key": "x"}})
    entries = detect_drift(snapshot, differ)
    assert "new_key" in entries[0].added_keys


def test_detects_removed_key():
    snapshot = _make_snapshot({"app/config": {"key": "val", "gone": "bye"}})
    differ = _make_differ({"app/config": {"key": "val"}})
    entries = detect_drift(snapshot, differ)
    assert "gone" in entries[0].removed_keys


def test_handles_missing_live_path_gracefully():
    snapshot = _make_snapshot({"app/missing": {"key": "val"}})
    differ = _make_differ({})
    entries = detect_drift(snapshot, differ)
    assert "key" in entries[0].removed_keys


def test_to_dict_structure():
    entry = DriftEntry(path="app/x", added_keys=["a"], removed_keys=["b"], changed_keys=["c"])
    d = entry.to_dict()
    assert d["path"] == "app/x"
    assert d["added_keys"] == ["a"]
    assert d["removed_keys"] == ["b"]
    assert d["changed_keys"] == ["c"]


def test_drift_command_text_output(tmp_path):
    from vaultdiff.cli_drift import drift_command
    from vaultdiff import snapshot as snap_mod
    from unittest.mock import patch

    snap_file = tmp_path / "snap.json"
    snapshot = _make_snapshot({"app/cfg": {"k": "old"}})

    runner = CliRunner()
    with patch("vaultdiff.cli_drift.load_snapshot", return_value=snapshot), \
         patch("vaultdiff.cli_drift.VaultClient"), \
         patch("vaultdiff.cli_drift.detect_drift", return_value=[
             DriftEntry(path="app/cfg", changed_keys=["k"])
         ]):
        result = runner.invoke(drift_command, [
            str(snap_file),
            "--vault-addr", "http://localhost:8200",
            "--vault-token", "root",
        ])

    assert "[DRIFT] app/cfg" in result.output
    assert "~ k" in result.output
