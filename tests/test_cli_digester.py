"""Tests for vaultdiff.cli_digester.digest_command."""
from __future__ import annotations

from contextlib import contextmanager
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from vaultdiff.cli_digester import digest_command
from vaultdiff.differ import SecretDiff
from vaultdiff.digester import DigestEntry, DigestReport
from vaultdiff.vault_client import VaultClientError


_SAME_DATA = {"api_key": "abc123"}


def _matching_report():
    import hashlib, json
    d = hashlib.sha256(json.dumps(_SAME_DATA, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    return DigestReport(entries=[DigestEntry(path="sec/a", left_digest=d, right_digest=d)])


def _mismatch_report():
    return DigestReport(entries=[DigestEntry(path="sec/a", left_digest="aaa", right_digest="bbb")])


@contextmanager
def _patch_deps(report):
    with patch("vaultdiff.cli_digester.VaultClient") as mock_vc, \
         patch("vaultdiff.cli_digester.VaultDiffer") as mock_differ, \
         patch("vaultdiff.cli_digester.digest_diffs", return_value=report):
        mock_differ.return_value.diff_secret.return_value = MagicMock(spec=SecretDiff)
        yield mock_vc, mock_differ


_BASE_ARGS = [
    "--left-addr", "http://left",
    "--left-token", "tok-l",
    "--right-addr", "http://right",
    "--right-token", "tok-r",
    "--path", "sec/a",
]


def test_digest_text_output_match():
    runner = CliRunner()
    with _patch_deps(_matching_report()):
        result = runner.invoke(digest_command, _BASE_ARGS)
    assert result.exit_code == 0
    assert "MATCH" in result.output


def test_digest_text_output_mismatch():
    runner = CliRunner()
    with _patch_deps(_mismatch_report()):
        result = runner.invoke(digest_command, _BASE_ARGS)
    assert result.exit_code == 0
    assert "MISMATCH" in result.output


def test_digest_json_output():
    runner = CliRunner()
    with _patch_deps(_matching_report()):
        result = runner.invoke(digest_command, _BASE_ARGS + ["--format", "json"])
    assert result.exit_code == 0
    assert "all_match" in result.output


def test_digest_exit_code_on_mismatch():
    runner = CliRunner()
    with _patch_deps(_mismatch_report()):
        result = runner.invoke(digest_command, _BASE_ARGS + ["--exit-code"])
    assert result.exit_code == 1


def test_digest_no_exit_code_flag_exits_zero_even_with_mismatch():
    runner = CliRunner()
    with _patch_deps(_mismatch_report()):
        result = runner.invoke(digest_command, _BASE_ARGS)
    assert result.exit_code == 0


def test_digest_vault_client_error_exits_1():
    runner = CliRunner()
    with patch("vaultdiff.cli_digester.VaultClient", side_effect=VaultClientError("bad token")):
        result = runner.invoke(digest_command, _BASE_ARGS)
    assert result.exit_code == 1
    assert "Vault connection error" in result.output
