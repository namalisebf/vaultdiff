"""Tests for vaultdiff.cli_ranker."""
from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

from click.testing import CliRunner

from vaultdiff.cli_ranker import rank_command
from vaultdiff.differ import SecretDiff
from vaultdiff.vault_client import VaultClientError

_BASE_ARGS = [
    "--left-addr", "http://left:8200",
    "--left-token", "tok-l",
    "--right-addr", "http://right:8200",
    "--right-token", "tok-r",
    "--path", "secret/app",
]


def _clean_diff(path: str = "secret/app") -> SecretDiff:
    return SecretDiff(path=path, changed_keys={}, only_in_left={}, only_in_right={})


def _patch_deps(diff: SecretDiff):
    return patch.multiple(
        "vaultdiff.cli_ranker",
        VaultClient=MagicMock(return_value=MagicMock()),
        VaultDiffer=MagicMock(return_value=MagicMock(diff_secret=MagicMock(return_value=diff))),
    )


def test_rank_text_output_no_changes():
    diff = _clean_diff()
    with _patch_deps(diff):
        result = CliRunner().invoke(rank_command, _BASE_ARGS)
    assert result.exit_code == 0
    assert "secret/app" in result.output
    assert "low" in result.output


def test_rank_json_output():
    diff = _clean_diff()
    with _patch_deps(diff):
        result = CliRunner().invoke(rank_command, _BASE_ARGS + ["--format", "json"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert isinstance(data, list)
    assert data[0]["path"] == "secret/app"
    assert "tier" in data[0]
    assert "weighted_score" in data[0]


def test_rank_top_limits_results():
    diffs = [
        SecretDiff(path=f"secret/p{i}", changed_keys={}, only_in_left={}, only_in_right={})
        for i in range(5)
    ]
    differ_mock = MagicMock()
    differ_mock.diff_secret.side_effect = diffs
    args = [
        "--left-addr", "http://left:8200",
        "--left-token", "tok-l",
        "--right-addr", "http://right:8200",
        "--right-token", "tok-r",
    ]
    for i in range(5):
        args += ["--path", f"secret/p{i}"]
    args += ["--top", "2", "--format", "json"]
    with patch.multiple(
        "vaultdiff.cli_ranker",
        VaultClient=MagicMock(return_value=MagicMock()),
        VaultDiffer=MagicMock(return_value=differ_mock),
    ):
        result = CliRunner().invoke(rank_command, args)
    assert result.exit_code == 0
    assert len(json.loads(result.output)) == 2


def test_rank_vault_client_error_exits_1():
    with patch("vaultdiff.cli_ranker.VaultClient", side_effect=VaultClientError("bad token")):
        result = CliRunner().invoke(rank_command, _BASE_ARGS)
    assert result.exit_code == 1
    assert "Error" in result.output


def test_rank_empty_paths_shows_message():
    differ_mock = MagicMock(diff_secret=MagicMock(return_value=_clean_diff()))
    with patch.multiple(
        "vaultdiff.cli_ranker",
        VaultClient=MagicMock(return_value=MagicMock()),
        VaultDiffer=MagicMock(return_value=differ_mock),
    ):
        result = CliRunner().invoke(rank_command, [
            "--left-addr", "http://left:8200",
            "--left-token", "tok-l",
            "--right-addr", "http://right:8200",
            "--right-token", "tok-r",
            "--path", "secret/app",
            "--top", "0",
        ])
    assert result.exit_code == 0
