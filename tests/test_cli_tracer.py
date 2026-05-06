"""Unit tests for vaultdiff.cli_tracer."""
from __future__ import annotations

import json
from contextlib import contextmanager
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from vaultdiff.cli_tracer import trace_command
from vaultdiff.differ import SecretDiff
from vaultdiff.tracer import TracePoint, TraceReport
from vaultdiff.vault_client import VaultClientError


def _clean_diff(path: str = "secret/app") -> SecretDiff:
    return SecretDiff(path=path, changed_keys={}, only_in_left={}, only_in_right={})


def _changed_diff(path: str = "secret/app") -> SecretDiff:
    return SecretDiff(
        path=path,
        changed_keys={"KEY": ("old", "new")},
        only_in_left={},
        only_in_right={},
    )


@contextmanager
 def _patch_deps(diff_result=None):
    if diff_result is None:
        diff_result = _clean_diff()
    mock_client = MagicMock()
    mock_differ = MagicMock()
    mock_differ.diff_secret.return_value = diff_result
    with patch("vaultdiff.cli_tracer.VaultClient", return_value=mock_client), \
         patch("vaultdiff.cli_tracer.VaultDiffer", return_value=mock_differ):
        yield mock_differ


def test_trace_clean_text_output():
    runner = CliRunner()
    with _patch_deps(_clean_diff()):
        result = runner.invoke(
            trace_command,
            ["--env", "prod:http://a:http://b", "--path", "secret/app", "--token", "tok"],
        )
    assert result.exit_code == 0
    assert "CLEAN" in result.output


def test_trace_changed_text_output():
    runner = CliRunner()
    with _patch_deps(_changed_diff()):
        result = runner.invoke(
            trace_command,
            ["--env", "prod:http://a:http://b", "--path", "secret/app", "--token", "tok"],
        )
    assert result.exit_code == 0
    assert "CHANGED" in result.output
    assert "~ KEY" in result.output


def test_trace_json_output():
    runner = CliRunner()
    with _patch_deps(_clean_diff()):
        result = runner.invoke(
            trace_command,
            [
                "--env", "prod:http://a:http://b",
                "--path", "secret/app",
                "--token", "tok",
                "--format", "json",
            ],
        )
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert "points" in data
    assert "total_changes" in data


def test_trace_vault_client_error_exits_1():
    runner = CliRunner()
    with patch("vaultdiff.cli_tracer.VaultClient", side_effect=VaultClientError("boom")):
        result = runner.invoke(
            trace_command,
            ["--env", "prod:http://a:http://b", "--path", "secret/app", "--token", "tok"],
        )
    assert result.exit_code == 1
    assert "Vault error" in result.output


def test_trace_bad_env_format_exits_1():
    runner = CliRunner()
    result = runner.invoke(
        trace_command,
        ["--env", "bad-format", "--path", "secret/app", "--token", "tok"],
    )
    assert result.exit_code == 1
