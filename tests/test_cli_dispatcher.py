"""Unit tests for vaultdiff.cli_dispatcher."""
from __future__ import annotations

import json
from contextlib import contextmanager
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from vaultdiff.cli_dispatcher import dispatch_command
from vaultdiff.differ import SecretDiff
from vaultdiff.dispatcher import DispatchReport
from vaultdiff.vault_client import VaultClientError


def _diff(path: str) -> SecretDiff:
    d = MagicMock(spec=SecretDiff)
    d.path = path
    return d


@contextmanager
def _patch_deps(diffs, report=None):
    mock_differ = MagicMock()
    mock_differ.diff_secret.side_effect = diffs

    mock_dispatcher = MagicMock()
    mock_dispatcher.dispatch.return_value = report or DispatchReport(
        dispatched={"default": [diffs[0]] if diffs else []}
    )

    with patch("vaultdiff.cli_dispatcher.VaultClient"), \
         patch("vaultdiff.cli_dispatcher.VaultDiffer", return_value=mock_differ), \
         patch("vaultdiff.cli_dispatcher.Dispatcher", return_value=mock_dispatcher):
        yield mock_differ, mock_dispatcher


BASE_ARGS = [
    "--left-addr", "http://left",
    "--left-token", "tok-l",
    "--right-addr", "http://right",
    "--right-token", "tok-r",
    "--path", "secret/prod/db",
]


def test_dispatch_text_output():
    d = _diff("secret/prod/db")
    report = DispatchReport(dispatched={"prod": [d]})
    with _patch_deps([d], report=report):
        runner = CliRunner()
        result = runner.invoke(dispatch_command, BASE_ARGS + ["--rule", "prod:secret/prod/*"])
    assert result.exit_code == 0
    assert "secret/prod/db" in result.output
    assert "prod" in result.output


def test_dispatch_json_output():
    d = _diff("secret/prod/db")
    report = DispatchReport(dispatched={"prod": [d]})
    with _patch_deps([d], report=report):
        runner = CliRunner()
        result = runner.invoke(
            dispatch_command,
            BASE_ARGS + ["--rule", "prod:secret/prod/*", "--format", "json"],
        )
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert "prod" in data


def test_dispatch_vault_client_error_exits_1():
    with patch("vaultdiff.cli_dispatcher.VaultClient",
               side_effect=VaultClientError("bad token")):
        runner = CliRunner()
        result = runner.invoke(dispatch_command, BASE_ARGS)
    assert result.exit_code == 1
    assert "Error" in result.output


def test_dispatch_invalid_rule_exits_1():
    with _patch_deps([_diff("secret/prod/db")]):
        runner = CliRunner()
        result = runner.invoke(dispatch_command, BASE_ARGS + ["--rule", "badformat"])
    assert result.exit_code == 1


def test_dispatch_diff_error_exits_1():
    with patch("vaultdiff.cli_dispatcher.VaultClient"), \
         patch("vaultdiff.cli_dispatcher.VaultDiffer") as mock_differ_cls:
        mock_differ = MagicMock()
        mock_differ.diff_secret.side_effect = VaultClientError("not found")
        mock_differ_cls.return_value = mock_differ
        runner = CliRunner()
        result = runner.invoke(dispatch_command, BASE_ARGS)
    assert result.exit_code == 1
