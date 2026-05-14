"""Tests for vaultdiff.cli_pruner2."""
from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from vaultdiff.cli_pruner2 import prune2_command
from vaultdiff.differ import SecretDiff
from vaultdiff.pruner2 import ScorePruneReport
from vaultdiff.vault_client import VaultClientError


def _clean_diff(path="secret/a"):
    return SecretDiff(path=path, changed_keys={}, only_in_left={}, only_in_right={})


def _dirty_diff(path="secret/b"):
    return SecretDiff(
        path=path,
        changed_keys={"key": ("old", "new")},
        only_in_left={},
        only_in_right={},
    )


def _patch_deps(diffs):
    return patch.multiple(
        "vaultdiff.cli_pruner2",
        VaultClient=MagicMock(),
        VaultDiffer=MagicMock(
            return_value=MagicMock(diff_secret=MagicMock(side_effect=diffs))
        ),
    )


BASE_ARGS = [
    "--left-addr", "http://left",
    "--left-token", "tok-l",
    "--right-addr", "http://right",
    "--right-token", "tok-r",
    "--path", "secret/a",
]


def test_prune2_text_output_clean():
    runner = CliRunner()
    with _patch_deps([_clean_diff()]):
        result = runner.invoke(prune2_command, BASE_ARGS)
    assert result.exit_code == 0
    assert "Kept:" in result.output
    assert "Dropped:" in result.output


def test_prune2_drop_clean_removes_clean_diff():
    runner = CliRunner()
    with _patch_deps([_clean_diff()]):
        result = runner.invoke(prune2_command, BASE_ARGS + ["--drop-clean"])
    assert result.exit_code == 0
    assert "Kept:    0" in result.output
    assert "Dropped: 1" in result.output


def test_prune2_json_output():
    runner = CliRunner()
    with _patch_deps([_dirty_diff()]):
        result = runner.invoke(prune2_command, BASE_ARGS + ["--format", "json"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert "total_kept" in data
    assert "total_dropped" in data


def test_prune2_vault_client_error_exits_1():
    runner = CliRunner()
    with patch("vaultdiff.cli_pruner2.VaultClient", side_effect=VaultClientError("bad")):
        result = runner.invoke(prune2_command, BASE_ARGS)
    assert result.exit_code == 1
    assert "Error" in result.output
