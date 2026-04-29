"""Tests for vaultdiff.watchdog."""
from unittest.mock import MagicMock

import pytest

from vaultdiff.drift import DriftEntry
from vaultdiff.snapshot import Snapshot, SnapshotEntry
from vaultdiff.watchdog import WatchEvent, Watchdog, WatchdogConfig


def _make_snapshot(data: dict) -> Snapshot:
    entries = [
        SnapshotEntry(path=path, data=vals) for path, vals in data.items()
    ]
    snap = Snapshot(entries=entries)
    return snap


def _make_watchdog(baseline_data: dict, current_data: dict, on_change=None, on_error=None):
    snapshot = _make_snapshot(baseline_data)
    mock_client = MagicMock()
    mock_client.read_secret.side_effect = lambda p: current_data.get(p, {})
    mock_differ = MagicMock()
    mock_differ.client_left = mock_client
    config = WatchdogConfig(
        paths=list(current_data.keys()) or list(baseline_data.keys()),
        baseline_snapshot=snapshot,
        on_change=on_change,
        on_error=on_error,
    )
    return Watchdog(config, mock_differ)


def test_watch_event_has_changes_false_when_no_drift():
    event = WatchEvent(path="secret/app", drift_entries=[
        DriftEntry(path="secret/app", key="DB_PASS", status="unchanged", left="x", right="x")
    ])
    assert not event.has_changes()


def test_watch_event_has_changes_true_when_drift():
    event = WatchEvent(path="secret/app", drift_entries=[
        DriftEntry(path="secret/app", key="DB_PASS", status="changed", left="old", right="new")
    ])
    assert event.has_changes()


def test_watch_event_to_dict_only_includes_drifted():
    event = WatchEvent(path="secret/app", drift_entries=[
        DriftEntry(path="secret/app", key="A", status="unchanged", left="v", right="v"),
        DriftEntry(path="secret/app", key="B", status="changed", left="old", right="new"),
    ])
    d = event.to_dict()
    assert d["path"] == "secret/app"
    assert len(d["changes"]) == 1
    assert d["changes"][0]["key"] == "B"


def test_run_once_no_changes_does_not_call_on_change():
    callback = MagicMock()
    wd = _make_watchdog(
        baseline_data={"secret/app": {"KEY": "val"}},
        current_data={"secret/app": {"KEY": "val"}},
        on_change=callback,
    )
    events = wd.run_once()
    callback.assert_not_called()
    assert len(events) == 1
    assert not events[0].has_changes()


def test_run_once_changed_key_triggers_on_change():
    callback = MagicMock()
    wd = _make_watchdog(
        baseline_data={"secret/app": {"KEY": "old"}},
        current_data={"secret/app": {"KEY": "new"}},
        on_change=callback,
    )
    events = wd.run_once()
    callback.assert_called_once()
    assert events[0].has_changes()


def test_run_once_exception_calls_on_error():
    snapshot = _make_snapshot({"secret/app": {"KEY": "val"}})
    mock_client = MagicMock()
    mock_client.read_secret.side_effect = RuntimeError("boom")
    mock_differ = MagicMock()
    mock_differ.client_left = mock_client
    error_cb = MagicMock()
    config = WatchdogConfig(
        paths=["secret/app"],
        baseline_snapshot=snapshot,
        on_error=error_cb,
    )
    wd = Watchdog(config, mock_differ)
    events = wd.run_once()
    error_cb.assert_called_once()
    assert events == []
