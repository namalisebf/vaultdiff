"""Tests for vaultdiff.cli_scorer2."""
from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

from click.testing import CliRunner

from vaultdiff.cli_scorer2 import weighted_score_command
from vaultdiff.differ import SecretDiff
from vaultdiff.scorer2 import ScoredEntry, WeightedScoreReport
from vaultdiff.vault_client import VaultClientError

_BASE_ARGS = [
    "--left-addr", "http://left",
    "--left-token", "tok-l",
    "--right-addr", "http://right",
    "--right-token", "tok-r",
    "--path", "secret/app",
]


def _clean_diff() -> SecretDiff:
    return SecretDiff(path="secret/app", changed_keys={}, only_in_left={}, only_in_right={})


def _patch_deps(diffs=None, client_error=None):
    if diffs is None:
        diffs = [_clean_diff()]

    def _inner(fn):
        import functools

        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            with patch("vaultdiff.cli_scorer2.VaultClient") as mock_vc, \
                 patch("vaultdiff.cli_scorer2.VaultDiffer") as mock_vd:
                if client_error:
                    mock_vc.side_effect = client_error
                else:
                    mock_vd.return_value.diff_secret.side_effect = lambda p: next(
                        (d for d in diffs if d.path == p), _clean_diff()
                    )
                fn(*args, mock_vc=mock_vc, mock_vd=mock_vd, **kwargs)
        return wrapper
    return _inner


def test_weighted_score_text_output_clean():
    runner = CliRunner()
    with patch("vaultdiff.cli_scorer2.VaultClient"), \
         patch("vaultdiff.cli_scorer2.VaultDiffer") as mock_vd:
        mock_vd.return_value.diff_secret.return_value = _clean_diff()
        result = runner.invoke(weighted_score_command, _BASE_ARGS)
    assert result.exit_code == 0
    assert "secret/app" in result.output
    assert "score=0.0" in result.output


def test_weighted_score_json_output():
    runner = CliRunner()
    with patch("vaultdiff.cli_scorer2.VaultClient"), \
         patch("vaultdiff.cli_scorer2.VaultDiffer") as mock_vd:
        d = SecretDiff(path="secret/app", changed_keys={"k": ("a", "b")}, only_in_left={}, only_in_right={})
        mock_vd.return_value.diff_secret.return_value = d
        result = runner.invoke(weighted_score_command, _BASE_ARGS + ["--format", "json"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert "total_score" in data
    assert data["total_score"] == 3.0


def test_weighted_score_top_limits_output():
    runner = CliRunner()
    with patch("vaultdiff.cli_scorer2.VaultClient"), \
         patch("vaultdiff.cli_scorer2.VaultDiffer") as mock_vd:
        mock_vd.return_value.diff_secret.side_effect = [
            SecretDiff(path="secret/a", changed_keys={"k": ("a", "b")}, only_in_left={}, only_in_right={}),
            SecretDiff(path="secret/b", changed_keys={}, only_in_left={}, only_in_right={}),
        ]
        result = runner.invoke(
            weighted_score_command,
            _BASE_ARGS + ["--path", "secret/b", "--top", "1"],
        )
    assert result.exit_code == 0
    assert "secret/b" not in result.output


def test_weighted_score_vault_client_error_exits_1():
    runner = CliRunner()
    with patch("vaultdiff.cli_scorer2.VaultClient", side_effect=VaultClientError("bad token")):
        result = runner.invoke(weighted_score_command, _BASE_ARGS)
    assert result.exit_code == 1
    assert "Error" in result.output
