"""Tests for the CLI interface."""

from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from vaultdiff.cli import cli
from vaultdiff.vault_client import VaultClientError
from vaultdiff.differ import SecretDiff
from vaultdiff.formatter import OutputFormat


BASE_ARGS = [
    "diff",
    "secret/app/dev",
    "secret/app/prod",
    "--left-url", "http://vault-left:8200",
    "--right-url", "http://vault-right:8200",
    "--left-token", "left-token",
    "--right-token", "right-token",
]


def _no_diff():
    return SecretDiff(path="secret/app/dev", changed={}, only_in_left=set(), only_in_right=set())


@patch("vaultdiff.cli.Reporter")
@patch("vaultdiff.cli.VaultDiffer")
@patch("vaultdiff.cli.VaultClient")
def test_diff_command_success(mock_client_cls, mock_differ_cls, mock_reporter_cls):
    runner = CliRunner()
    mock_reporter = MagicMock()
    mock_reporter.report_path.return_value = False
    mock_reporter_cls.return_value = mock_reporter

    result = runner.invoke(cli, BASE_ARGS)

    assert result.exit_code == 0
    mock_reporter.report_path.assert_called_once_with("secret/app/dev", "secret/app/prod")


@patch("vaultdiff.cli.Reporter")
@patch("vaultdiff.cli.VaultDiffer")
@patch("vaultdiff.cli.VaultClient")
def test_diff_command_exit_code_when_differences(mock_client_cls, mock_differ_cls, mock_reporter_cls):
    runner = CliRunner()
    mock_reporter = MagicMock()
    mock_reporter.report_path.return_value = True
    mock_reporter_cls.return_value = mock_reporter

    result = runner.invoke(cli, BASE_ARGS + ["--exit-code"])

    assert result.exit_code == 1


@patch("vaultdiff.cli.VaultClient", side_effect=VaultClientError("auth failed"))
def test_diff_command_vault_client_error(mock_client_cls):
    runner = CliRunner()
    result = runner.invoke(cli, BASE_ARGS)

    assert result.exit_code == 2
    assert "auth failed" in result.output


@patch("vaultdiff.cli.Reporter")
@patch("vaultdiff.cli.VaultDiffer")
@patch("vaultdiff.cli.VaultClient")
def test_diff_command_recursive(mock_client_cls, mock_differ_cls, mock_reporter_cls):
    runner = CliRunner()
    mock_reporter = MagicMock()
    mock_reporter.report_recursive.return_value = False
    mock_reporter_cls.return_value = mock_reporter

    result = runner.invoke(cli, BASE_ARGS + ["--recursive"])

    assert result.exit_code == 0
    mock_reporter.report_recursive.assert_called_once_with("secret/app/dev", "secret/app/prod")


@patch("vaultdiff.cli.Reporter")
@patch("vaultdiff.cli.VaultDiffer")
@patch("vaultdiff.cli.VaultClient")
def test_diff_command_json_format(mock_client_cls, mock_differ_cls, mock_reporter_cls):
    runner = CliRunner()
    mock_reporter = MagicMock()
    mock_reporter.report_path.return_value = False
    mock_reporter_cls.return_value = mock_reporter

    result = runner.invoke(cli, BASE_ARGS + ["--format", "json"])

    assert result.exit_code == 0
    _, kwargs = mock_reporter_cls.call_args
    assert kwargs["output_format"] == OutputFormat.JSON
