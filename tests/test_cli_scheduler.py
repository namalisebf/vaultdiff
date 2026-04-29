"""Tests for vaultdiff.cli_scheduler."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from click.testing import CliRunner

from vaultdiff.cli_scheduler import schedule_command
from vaultdiff.vault_client import VaultClientError

_BASE_ARGS = [
    "--left-addr", "http://left:8200",
    "--left-token", "tok-left",
    "--right-addr", "http://right:8200",
    "--right-token", "tok-right",
    "--path", "secret/app",
    "--runs", "1",
]


def _patch_deps(diff_has_differences: bool = False):
    diff = MagicMock()
    diff.has_differences.return_value = diff_has_differences

    differ = MagicMock()
    differ.diff_secret.return_value = diff

    patches = [
        patch("vaultdiff.cli_scheduler.VaultClient"),
        patch("vaultdiff.cli_scheduler.VaultDiffer", return_value=differ),
    ]
    return patches, differ


def test_schedule_runs_and_exits_cleanly():
    patches, differ = _patch_deps(diff_has_differences=False)
    runner = CliRunner()
    with patches[0], patches[1]:
        result = runner.invoke(schedule_command, _BASE_ARGS)
    assert result.exit_code == 0
    differ.diff_secret.assert_called_once_with("secret/app", "secret/app")


def test_schedule_vault_client_error_exits_1():
    runner = CliRunner()
    with patch("vaultdiff.cli_scheduler.VaultClient", side_effect=VaultClientError("bad token")):
        result = runner.invoke(schedule_command, _BASE_ARGS)
    assert result.exit_code == 1
    assert "Vault connection error" in result.output


def test_schedule_on_diff_callback_prints_output():
    patches, differ = _patch_deps(diff_has_differences=True)
    runner = CliRunner()
    with patches[0], patches[1]:
        result = runner.invoke(schedule_command, _BASE_ARGS)
    assert result.exit_code == 0


def test_schedule_multiple_paths():
    patches, differ = _patch_deps()
    args = _BASE_ARGS + ["--path", "secret/db", "--runs", "1"]
    runner = CliRunner()
    with patches[0], patches[1]:
        result = runner.invoke(schedule_command, args)
    assert result.exit_code == 0
    assert differ.diff_secret.call_count == 2


def test_schedule_error_in_diff_does_not_crash():
    runner = CliRunner()
    differ = MagicMock()
    differ.diff_secret.side_effect = RuntimeError("vault down")
    with patch("vaultdiff.cli_scheduler.VaultClient"), \
         patch("vaultdiff.cli_scheduler.VaultDiffer", return_value=differ):
        result = runner.invoke(schedule_command, _BASE_ARGS)
    assert result.exit_code == 0
    assert "ERROR" in result.output
