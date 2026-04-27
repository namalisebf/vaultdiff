"""Tests for the vaultdiff export CLI sub-command."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from vaultdiff.cli_export import export_command
from vaultdiff.differ import SecretDiff
from vaultdiff.vault_client import VaultClientError


BASE_ARGS = [
    "--left-addr", "http://left:8200",
    "--right-addr", "http://right:8200",
    "--left-token", "tok-left",
    "--right-token", "tok-right",
    "--path", "secret/app",
]


def _no_diff(path: str) -> SecretDiff:
    return SecretDiff(path=path, changed={}, only_in_left={}, only_in_right={})


def _patch_deps(differ_instance):
    """Return a context manager that patches VaultClient and VaultDiffer."""
    client_patch = patch("vaultdiff.cli_export.VaultClient", return_value=MagicMock())
    differ_patch = patch("vaultdiff.cli_export.VaultDiffer", return_value=differ_instance)
    return client_patch, differ_patch


def test_export_json_writes_file(tmp_path):
    out_file = str(tmp_path / "result.json")
    differ = MagicMock()
    differ.diff_secret.return_value = _no_diff("secret/app")

    cp, dp = _patch_deps(differ)
    runner = CliRunner()
    with cp, dp:
        result = runner.invoke(
            export_command,
            BASE_ARGS + ["--output", out_file, "--format", "json"],
        )

    assert result.exit_code == 0, result.output
    with open(out_file) as fh:
        data = json.load(fh)
    assert isinstance(data, list)
    assert data[0]["path"] == "secret/app"


def test_export_csv_writes_file(tmp_path):
    out_file = str(tmp_path / "result.csv")
    differ = MagicMock()
    differ.diff_secret.return_value = SecretDiff(
        path="secret/app",
        changed={"KEY": ("v1", "v2")},
        only_in_left={},
        only_in_right={},
    )

    cp, dp = _patch_deps(differ)
    runner = CliRunner()
    with cp, dp:
        result = runner.invoke(
            export_command,
            BASE_ARGS + ["--output", out_file, "--format", "csv"],
        )

    assert result.exit_code == 0, result.output
    with open(out_file) as fh:
        content = fh.read()
    assert "changed" in content
    assert "KEY" in content


def test_export_exits_on_vault_error():
    runner = CliRunner()
    with patch("vaultdiff.cli_export.VaultClient", side_effect=VaultClientError("auth failed")):
        result = runner.invoke(
            export_command,
            BASE_ARGS + ["--output", "/tmp/out.json"],
        )
    assert result.exit_code == 2
    assert "Vault connection error" in result.output


def test_export_exits_on_diff_error():
    differ = MagicMock()
    differ.diff_secret.side_effect = VaultClientError("path not found")
    cp, dp = _patch_deps(differ)
    runner = CliRunner()
    with cp, dp:
        result = runner.invoke(
            export_command,
            BASE_ARGS + ["--output", "/tmp/out.json"],
        )
    assert result.exit_code == 2
    assert "Error reading" in result.output
