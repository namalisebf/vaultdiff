"""Integration-style tests for CLI wiring (env vars, missing options)."""

import os
from unittest.mock import MagicMock, patch

from click.testing import CliRunner

from vaultdiff.cli import cli


BASE_ENV = {
    "VAULT_LEFT_ADDR": "http://vault-left:8200",
    "VAULT_RIGHT_ADDR": "http://vault-right:8200",
    "VAULT_LEFT_TOKEN": "left-token",
    "VAULT_RIGHT_TOKEN": "right-token",
}


@patch("vaultdiff.cli.Reporter")
@patch("vaultdiff.cli.VaultDiffer")
@patch("vaultdiff.cli.VaultClient")
def test_diff_reads_tokens_from_env(mock_client_cls, mock_differ_cls, mock_reporter_cls):
    runner = CliRunner()
    mock_reporter = MagicMock()
    mock_reporter.report_path.return_value = False
    mock_reporter_cls.return_value = mock_reporter

    result = runner.invoke(
        cli,
        ["diff", "secret/a", "secret/b"],
        env=BASE_ENV,
    )

    assert result.exit_code == 0
    calls = mock_client_cls.call_args_list
    assert len(calls) == 2
    left_kwargs = calls[0][1]
    right_kwargs = calls[1][1]
    assert left_kwargs["token"] == "left-token"
    assert right_kwargs["token"] == "right-token"


def test_diff_missing_required_options_shows_error():
    runner = CliRunner()
    result = runner.invoke(cli, ["diff", "secret/a", "secret/b"])
    assert result.exit_code != 0
    assert "Missing option" in result.output or "Error" in result.output


@patch("vaultdiff.cli.Reporter")
@patch("vaultdiff.cli.VaultDiffer")
@patch("vaultdiff.cli.VaultClient")
def test_diff_no_exit_code_flag_exits_zero_even_with_diffs(
    mock_client_cls, mock_differ_cls, mock_reporter_cls
):
    runner = CliRunner()
    mock_reporter = MagicMock()
    mock_reporter.report_path.return_value = True  # differences found
    mock_reporter_cls.return_value = mock_reporter

    result = runner.invoke(
        cli,
        ["diff", "secret/a", "secret/b"],
        env=BASE_ENV,
    )

    assert result.exit_code == 0
