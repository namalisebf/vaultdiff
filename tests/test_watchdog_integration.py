"""Integration-style tests for the watchdog using real Snapshot + DriftEntry logic."""
from vaultdiff.snapshot import Snapshot, SnapshotEntry
from vaultdiff.watchdog import Watchdog, WatchdogConfig, WatchEvent
from unittest.mock import MagicMock


def _build(baseline: dict, current: dict, paths=None, on_change=None, on_error=None):
    entries = [SnapshotEntry(path=p, data=d) for p, d in baseline.items()]
    snapshot = Snapshot(entries=entries)
    mock_client = MagicMock()
    mock_client.read_secret.side_effect = lambda p: current.get(p, {})
    mock_differ = MagicMock()
    mock_differ.client_left = mock_client
    config = WatchdogConfig(
        paths=paths or list(set(list(baseline) + list(current))),
        baseline_snapshot=snapshot,
        on_change=on_change,
        on_error=on_error,
    )
    return Watchdog(config, mock_differ)


def test_no_drift_produces_clean_events():
    wd = _build(
        baseline={"secret/db": {"PASS": "abc", "USER": "root"}},
        current={"secret/db": {"PASS": "abc", "USER": "root"}},
    )
    events = wd.run_once()
    assert len(events) == 1
    assert not events[0].has_changes()


def test_changed_value_detected():
    changed_events = []
    wd = _build(
        baseline={"secret/db": {"PASS": "old"}},
        current={"secret/db": {"PASS": "new"}},
        on_change=changed_events.append,
    )
    events = wd.run_once()
    assert events[0].has_changes()
    assert len(changed_events) == 1
    assert changed_events[0].path == "secret/db"


def test_added_key_detected():
    wd = _build(
        baseline={"secret/app": {}},
        current={"secret/app": {"NEW_KEY": "value"}},
    )
    events = wd.run_once()
    assert events[0].has_changes()


def test_removed_key_detected():
    wd = _build(
        baseline={"secret/app": {"OLD_KEY": "value"}},
        current={"secret/app": {}},
    )
    events = wd.run_once()
    assert events[0].has_changes()


def test_multiple_paths_all_checked():
    wd = _build(
        baseline={
            "secret/a": {"K": "v"},
            "secret/b": {"K": "v"},
        },
        current={
            "secret/a": {"K": "v"},
            "secret/b": {"K": "changed"},
        },
    )
    events = wd.run_once()
    assert len(events) == 2
    clean = [e for e in events if not e.has_changes()]
    dirty = [e for e in events if e.has_changes()]
    assert len(clean) == 1
    assert len(dirty) == 1
    assert dirty[0].path == "secret/b"
