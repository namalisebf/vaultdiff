"""Tests for vaultdiff.cli_labeler."""

import json
from unittest.mock import MagicMock, patch

from click.testing import CliRunner

from vaultdiff.cli_labeler import label_command
from vaultdiff.vault_client import VaultClientError
from vaultdiff.labeler import LabeledPath


def _patch_deps(labeled=None, vault_error=None):
    """Return a context manager that patches VaultClient and Labeler."""
    import contextlib

    @contextlib.contextmanager
    def _ctx():
        with patch("vaultdiff.cli_labeler.VaultClient") as mock_vc, \
             patch("vaultdiff.cli_labeler.Labeler") as mock_lb:
            instance = MagicMock()
            if vault_error:
                instance.list_secrets.side_effect = vault_error
            mock_vc.return_value = instance

            lb_instance = MagicMock()
            lb_instance.label_paths.return_value = labeled or []
            mock_lb.return_value = lb_instance

            yield mock_vc, mock_lb

    return _ctx()


BASE_ARGS = [
    "--left-addr", "http://vault:8200",
    "--left-token", "root",
    "--path", "secret/prod/db",
    "--label-rule", "prod:secret/prod/*",
]


def test_label_text_output_no_labels():
    labeled = [LabeledPath(path="secret/prod/db", labels=[])]
    with _patch_deps(labeled=labeled):
        runner = CliRunner()
        result = runner.invoke(label_command, BASE_ARGS)
    assert result.exit_code == 0
    assert "(none)" in result.output


def test_label_text_output_with_labels():
    labeled = [LabeledPath(path="secret/prod/db", labels=["prod"])]
    with _patch_deps(labeled=labeled):
        runner = CliRunner()
        result = runner.invoke(label_command, BASE_ARGS)
    assert result.exit_code == 0
    assert "prod" in result.output
    assert "secret/prod/db" in result.output


def test_label_json_output():
    labeled = [LabeledPath(path="secret/prod/db", labels=["prod", "sensitive"])]
    with _patch_deps(labeled=labeled):
        runner = CliRunner()
        result = runner.invoke(label_command, BASE_ARGS + ["--format", "json"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data[0]["path"] == "secret/prod/db"
    assert "prod" in data[0]["labels"]


def test_label_vault_client_error_exits_1():
    with _patch_deps(vault_error=VaultClientError("connection refused")):
        runner = CliRunner()
        result = runner.invoke(label_command, BASE_ARGS)
    assert result.exit_code == 1
    assert "Vault error" in result.output


def test_label_invalid_rule_exits_2():
    runner = CliRunner()
    args = [
        "--left-addr", "http://vault:8200",
        "--left-token", "root",
        "--path", "secret/prod/db",
        "--label-rule", "badformat",
    ]
    # No patching needed — should fail before Vault call
    with patch("vaultdiff.cli_labeler.VaultClient"):
        result = runner.invoke(label_command, args)
    assert result.exit_code == 2
    assert "Invalid rule" in result.output
