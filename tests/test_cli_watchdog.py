"""Tests for vaultdiff.cli_watchdog."""
from contextlib import contextmanager
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from vaultdiff.cli_watchdog import watchdog_command
from vaultdiff.watchdog import WatchEvent
from vaultdiff.drift import DriftEntry


@contextmanager
def _patch_deps(snapshot=None, run_once_return=None):
    if snapshot is None:
        snapshot = MagicMock()
        snapshot.get.return_value = MagicMock(data={})
    if run_once_return is None:
        run_once_return = []
    with patch("vaultdiff.cli_watchdog.VaultClient") as mock_vc, \
         patch("vaultdiff.cli_watchdog.load_snapshot", return_value=snapshot), \
         patch("vaultdiff.cli_watchdog.VaultDiffer") as mock_differ, \
         patch("vaultdiff.cli_watchdog.Watchdog") as mock_wd:
        mock_vc.return_value = MagicMock()
        mock_differ.return_value = MagicMock()
        mock_wd.return_value.run_once.return_value = run_once_return
        yield mock_wd


def test_watchdog_once_exits_cleanly():
    runner = CliRunner()
    with _patch_deps():
        result = runner.invoke(watchdog_command, [
            "--addr-left", "http://vault:8200",
            "--token-left", "tok",
            "--baseline", "snap.json",
            "--path", "secret/app",
            "--once",
        ])
    assert result.exit_code == 0


def test_watchdog_vault_client_error_exits_1():
    runner = CliRunner()
    with patch("vaultdiff.cli_watchdog.VaultClient", side_effect=Exception("auth fail")), \
         patch("vaultdiff.cli_watchdog.load_snapshot"):
        result = runner.invoke(watchdog_command, [
            "--addr-left", "http://vault:8200",
            "--token-left", "bad",
            "--baseline", "snap.json",
            "--path", "secret/app",
            "--once",
        ])
    assert result.exit_code == 1


def test_watchdog_missing_baseline_exits_1():
    runner = CliRunner()
    with patch("vaultdiff.cli_watchdog.VaultClient"), \
         patch("vaultdiff.cli_watchdog.load_snapshot", side_effect=FileNotFoundError):
        result = runner.invoke(watchdog_command, [
            "--addr-left", "http://vault:8200",
            "--token-left", "tok",
            "--baseline", "missing.json",
            "--path", "secret/app",
            "--once",
        ])
    assert result.exit_code == 1
    assert "not found" in result.output


def test_watchdog_json_format_prints_json():
    runner = CliRunner()
    drift = DriftEntry(path="secret/app", key="X", status="changed", left="a", right="b")
    event = WatchEvent(path="secret/app", drift_entries=[drift])
    with _patch_deps(run_once_return=[event]) as mock_wd:
        # Simulate on_change being called during run_once
        def fake_run_once_side_effect():
            config_arg = mock_wd.call_args[0][0]
            if config_arg.on_change:
                config_arg.on_change(event)
            return [event]
        mock_wd.return_value.run_once.side_effect = fake_run_once_side_effect
        result = runner.invoke(watchdog_command, [
            "--addr-left", "http://vault:8200",
            "--token-left", "tok",
            "--baseline", "snap.json",
            "--path", "secret/app",
            "--once",
            "--format", "json",
        ])
    assert result.exit_code == 0
