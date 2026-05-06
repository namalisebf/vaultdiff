"""Tests for vaultdiff.cli_classifier."""
from __future__ import annotations

import json
from contextlib import contextmanager
from unittest.mock import MagicMock, patch

from click.testing import CliRunner

from vaultdiff.cli_classifier import classify_command
from vaultdiff.classifier import ClassifiedPath
from vaultdiff.differ import SecretDiff
from vaultdiff.vault_client import VaultClientError


def _clean_diff(path: str) -> SecretDiff:
    return SecretDiff(path=path, changed_keys={}, only_in_left={}, only_in_right={})


@contextmanager
def _patch_deps(diffs, vault_error=None):
    with patch("vaultdiff.cli_classifier.VaultClient") as mock_vc, \
         patch("vaultdiff.cli_classifier.VaultDiffer") as mock_differ:
        if vault_error:
            mock_vc.side_effect = vault_error
        else:
            mock_differ.return_value.diff_secret.side_effect = (
                lambda p: next(d for d in diffs if d.path == p)
            )
        yield mock_vc, mock_differ


_BASE_ARGS = [
    "--left-addr", "http://left",
    "--left-token", "tok-l",
    "--right-addr", "http://right",
    "--right-token", "tok-r",
]


def test_classify_text_output_no_changes():
    diff = _clean_diff("secret/app")
    with _patch_deps([diff]):
        runner = CliRunner()
        result = runner.invoke(classify_command, _BASE_ARGS + ["secret/app"])
    assert result.exit_code == 0


def test_classify_json_output():
    diff = SecretDiff(
        path="secret/db",
        changed_keys={"password": ("old", "new")},
        only_in_left={},
        only_in_right={},
    )
    with _patch_deps([diff]):
        runner = CliRunner()
        result = runner.invoke(
            classify_command, _BASE_ARGS + ["--format", "json", "secret/db"]
        )
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data[0]["tier"] == "critical"
    assert data[0]["path"] == "secret/db"


def test_classify_vault_client_error_exits_1():
    runner = CliRunner()
    with patch("vaultdiff.cli_classifier.VaultClient", side_effect=VaultClientError("boom")):
        result = runner.invoke(classify_command, _BASE_ARGS + ["secret/x"])
    assert result.exit_code == 1
    assert "Vault error" in result.output


def test_classify_min_tier_filters_low():
    diff_low = SecretDiff(
        path="secret/low",
        changed_keys={"region": ("a", "b")},
        only_in_left={},
        only_in_right={},
    )
    diff_high = SecretDiff(
        path="secret/high",
        changed_keys={"api_key": ("x", "y")},
        only_in_left={},
        only_in_right={},
    )
    with _patch_deps([diff_low, diff_high]):
        runner = CliRunner()
        result = runner.invoke(
            classify_command,
            _BASE_ARGS + ["--min-tier", "high", "secret/low", "secret/high"],
        )
    assert result.exit_code == 0
    assert "secret/high" in result.output
    assert "secret/low" not in result.output
