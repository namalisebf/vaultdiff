"""Tests for vaultdiff.cli_inspector."""
from __future__ import annotations

import json
from contextlib import contextmanager
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from vaultdiff.cli_inspector import inspect_command
from vaultdiff.differ import SecretDiff
from vaultdiff.vault_client import VaultClientError


def _no_diff(path="secret/app") -> SecretDiff:
    return SecretDiff(
        path=path,
        left_data={"key": "val"},
        right_data={"key": "val"},
        changed_keys=[],
        only_in_left=[],
        only_in_right=[],
    )


def _changed_diff(path="secret/app") -> SecretDiff:
    return SecretDiff(
        path=path,
        left_data={"token": "aaa"},
        right_data={"token": "bbb"},
        changed_keys=["token"],
        only_in_left=[],
        only_in_right=[],
    )


@contextmanager
def _patch_deps(diff_result):
    with patch("vaultdiff.cli_inspector.VaultClient") as mock_vc, \
         patch("vaultdiff.cli_inspector.VaultDiffer") as mock_differ:
        mock_differ_inst = MagicMock()
        mock_differ_inst.diff_secret.return_value = diff_result
        mock_differ.return_value = mock_differ_inst
        yield mock_vc, mock_differ


BASE_ARGS = [
    "--left-addr", "http://left:8200",
    "--left-token", "lt",
    "--right-addr", "http://right:8200",
    "--right-token", "rt",
    "--path", "secret/app",
]


def test_inspect_text_output_no_differences():
    with _patch_deps(_no_diff()):
        runner = CliRunner()
        result = runner.invoke(inspect_command, BASE_ARGS)
    assert result.exit_code == 0
    assert "secret/app" in result.output
    assert "no differing keys" in result.output


def test_inspect_text_output_with_changed_key():
    with _patch_deps(_changed_diff()):
        runner = CliRunner()
        result = runner.invoke(inspect_command, BASE_ARGS)
    assert result.exit_code == 0
    assert "token" in result.output


def test_inspect_json_output():
    with _patch_deps(_changed_diff()):
        runner = CliRunner()
        result = runner.invoke(inspect_command, BASE_ARGS + ["--format", "json"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert isinstance(data, list)
    assert data[0]["path"] == "secret/app"
    assert any(k["key"] == "token" for k in data[0]["keys"])


def test_inspect_only_changed_flag_hides_clean_paths():
    with _patch_deps(_no_diff()):
        runner = CliRunner()
        result = runner.invoke(inspect_command, BASE_ARGS + ["--only-changed", "--format", "json"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data == []


def test_inspect_vault_client_error_exits_1():
    with patch("vaultdiff.cli_inspector.VaultClient", side_effect=VaultClientError("bad token")):
        runner = CliRunner()
        result = runner.invoke(inspect_command, BASE_ARGS)
    assert result.exit_code == 1
    assert "bad token" in result.output


def test_inspect_read_error_exits_1():
    with patch("vaultdiff.cli_inspector.VaultClient"), \
         patch("vaultdiff.cli_inspector.VaultDiffer") as mock_differ:
        inst = MagicMock()
        inst.diff_secret.side_effect = VaultClientError("not found")
        mock_differ.return_value = inst
        runner = CliRunner()
        result = runner.invoke(inspect_command, BASE_ARGS)
    assert result.exit_code == 1
    assert "not found" in result.output
