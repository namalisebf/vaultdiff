"""Tests for vaultdiff.cli_collector."""
from __future__ import annotations

from contextlib import contextmanager
from unittest.mock import MagicMock, patch

from click.testing import CliRunner

from vaultdiff.cli_collector import collect_command
from vaultdiff.differ import SecretDiff
from vaultdiff.vault_client import VaultClientError
from vaultdiff.collector import CollectionReport, CollectedEntry


def _clean_entry(path="secret/app"):
    return CollectedEntry(path=path, changed_keys=0, only_in_left=0, only_in_right=0, total_keys=0)


def _dirty_entry(path="secret/app"):
    return CollectedEntry(path=path, changed_keys=1, only_in_left=0, only_in_right=0, total_keys=1)


@contextmanager
def _patch_deps(report):
    with patch("vaultdiff.cli_collector.VaultClient") as mock_client_cls, \
         patch("vaultdiff.cli_collector.VaultDiffer") as mock_differ_cls, \
         patch("vaultdiff.cli_collector.collect_diffs", return_value=report):
        mock_differ_cls.return_value.diff_secret.return_value = SecretDiff(
            path="secret/app", changed_keys={}, only_in_left={}, only_in_right={}
        )
        yield mock_client_cls, mock_differ_cls


BASE_ARGS = [
    "--left-addr", "http://left",
    "--left-token", "tok-l",
    "--right-addr", "http://right",
    "--right-token", "tok-r",
    "--path", "secret/app",
]


def test_collect_text_output_clean():
    report = CollectionReport(entries=[_clean_entry()])
    with _patch_deps(report):
        result = CliRunner().invoke(collect_command, BASE_ARGS)
    assert result.exit_code == 0
    assert "CLEAN" in result.output
    assert "secret/app" in result.output


def test_collect_text_output_dirty():
    report = CollectionReport(entries=[_dirty_entry()])
    with _patch_deps(report):
        result = CliRunner().invoke(collect_command, BASE_ARGS)
    assert result.exit_code == 0
    assert "DIRTY" in result.output


def test_collect_json_output():
    import json
    report = CollectionReport(entries=[_clean_entry()])
    with _patch_deps(report):
        result = CliRunner().invoke(collect_command, BASE_ARGS + ["--format", "json"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert "entries" in data
    assert "total_paths" in data


def test_collect_exit_code_on_differences():
    report = CollectionReport(entries=[_dirty_entry()])
    with _patch_deps(report):
        result = CliRunner().invoke(collect_command, BASE_ARGS + ["--exit-code"])
    assert result.exit_code == 1


def test_collect_vault_client_error_exits_1():
    with patch("vaultdiff.cli_collector.VaultClient", side_effect=VaultClientError("boom")):
        result = CliRunner().invoke(collect_command, BASE_ARGS)
    assert result.exit_code == 1
    assert "Vault error" in result.output
