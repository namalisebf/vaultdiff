"""Tests for vaultdiff.cli_tagger2."""
from __future__ import annotations

from contextlib import contextmanager
from unittest.mock import MagicMock, patch

from click.testing import CliRunner

from vaultdiff.cli_tagger2 import tag2_command
from vaultdiff.differ import SecretDiff
from vaultdiff.vault_client import VaultClientError


def _make_diff(path: str, dirty: bool = False) -> SecretDiff:
    d = MagicMock(spec=SecretDiff)
    d.path = path
    d.changed_keys = {"k": ("a", "b")} if dirty else {}
    d.only_in_left = {}
    d.only_in_right = {}
    d.has_differences.return_value = dirty
    return d


@contextmanager
def _patch_deps(diffs):
    with patch("vaultdiff.cli_tagger2.VaultClient") as mock_client_cls, \
         patch("vaultdiff.cli_tagger2.VaultDiffer") as mock_differ_cls:
        mock_differ = MagicMock()
        mock_differ.diff_secret.side_effect = diffs
        mock_differ_cls.return_value = mock_differ
        yield mock_client_cls, mock_differ_cls


BASE_ARGS = [
    "--left-addr", "http://left",
    "--left-token", "tok-l",
    "--right-addr", "http://right",
    "--right-token", "tok-r",
    "--path", "secret/app",
]


def test_tag2_text_output_clean():
    with _patch_deps([_make_diff("secret/app", dirty=False)]):
        runner = CliRunner()
        result = runner.invoke(tag2_command, BASE_ARGS)
    assert result.exit_code == 0
    assert "secret/app" in result.output


def test_tag2_json_output():
    with _patch_deps([_make_diff("secret/app", dirty=True)]):
        runner = CliRunner()
        result = runner.invoke(tag2_command, BASE_ARGS + ["--format", "json"])
    assert result.exit_code == 0
    assert "secret/app" in result.output
    assert "tag" in result.output


def test_tag2_custom_tag_rule_applied():
    with _patch_deps([_make_diff("secret/prod/db", dirty=False)]):
        runner = CliRunner()
        result = runner.invoke(
            tag2_command,
            BASE_ARGS[:-2] + ["--path", "secret/prod/db",
                               "--tag", "secret/prod/*:production",
                               "--format", "json"],
        )
    assert result.exit_code == 0
    assert "production" in result.output


def test_tag2_vault_client_error_exits_1():
    with patch("vaultdiff.cli_tagger2.VaultClient",
               side_effect=VaultClientError("bad token")):
        runner = CliRunner()
        result = runner.invoke(tag2_command, BASE_ARGS)
    assert result.exit_code == 1
    assert "Error" in result.output


def test_tag2_invalid_tag_rule_exits_1():
    with _patch_deps([_make_diff("secret/app")]):
        runner = CliRunner()
        result = runner.invoke(
            tag2_command, BASE_ARGS + ["--tag", "no-colon-here"]
        )
    assert result.exit_code == 1
    assert "Invalid tag rule" in result.output
