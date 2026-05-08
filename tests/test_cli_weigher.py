"""Tests for vaultdiff.cli_weigher."""
from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

from click.testing import CliRunner

from vaultdiff.cli_weigher import weigh_command
from vaultdiff.differ import SecretDiff
from vaultdiff.vault_client import VaultClientError
from vaultdiff.weigher import WeighedPath


def _make_diff(path: str) -> SecretDiff:
    d = MagicMock(spec=SecretDiff)
    d.path = path
    return d


def _patch_deps(diffs=None, weighed=None):
    if diffs is None:
        diffs = [_make_diff("prod/db")]
    if weighed is None:
        weighed = [WeighedPath(path="prod/db", weight=1.0, matched_rule=None)]

    patches = [
        patch("vaultdiff.cli_weigher.VaultClient"),
        patch("vaultdiff.cli_weigher.VaultDiffer"),
        patch("vaultdiff.cli_weigher.weigh_diffs", return_value=weighed),
    ]
    return patches, diffs


BASE_ARGS = [
    "--left-addr", "http://left",
    "--left-token", "tok-l",
    "--right-addr", "http://right",
    "--right-token", "tok-r",
    "--path", "prod/db",
]


def test_weigh_text_output_no_rule():
    weighed = [WeighedPath(path="prod/db", weight=1.0, matched_rule=None)]
    ps, _ = _patch_deps(weighed=weighed)
    with ps[0], ps[1] as mock_differ_cls, ps[2]:
        mock_differ_cls.return_value.diff_secret.return_value = _make_diff("prod/db")
        runner = CliRunner()
        result = runner.invoke(weigh_command, BASE_ARGS)
    assert result.exit_code == 0
    assert "prod/db" in result.output
    assert "weight=1.00" in result.output


def test_weigh_text_output_with_rule():
    weighed = [WeighedPath(path="prod/db", weight=5.0, matched_rule="prod/*")]
    ps, _ = _patch_deps(weighed=weighed)
    with ps[0], ps[1] as mock_differ_cls, ps[2]:
        mock_differ_cls.return_value.diff_secret.return_value = _make_diff("prod/db")
        runner = CliRunner()
        result = runner.invoke(weigh_command, BASE_ARGS + ["--rule", "prod/*:5.0"])
    assert result.exit_code == 0
    assert "rule: prod/*" in result.output


def test_weigh_json_output():
    weighed = [WeighedPath(path="prod/db", weight=3.0, matched_rule="prod/*")]
    ps, _ = _patch_deps(weighed=weighed)
    with ps[0], ps[1] as mock_differ_cls, ps[2]:
        mock_differ_cls.return_value.diff_secret.return_value = _make_diff("prod/db")
        runner = CliRunner()
        result = runner.invoke(weigh_command, BASE_ARGS + ["--format", "json"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data[0]["path"] == "prod/db"
    assert data[0]["weight"] == 3.0


def test_weigh_vault_client_error_exits_1():
    with patch("vaultdiff.cli_weigher.VaultClient", side_effect=VaultClientError("boom")):
        runner = CliRunner()
        result = runner.invoke(weigh_command, BASE_ARGS)
    assert result.exit_code == 1
    assert "Vault error" in result.output


def test_weigh_invalid_rule_format_exits_1():
    ps, _ = _patch_deps()
    with ps[0], ps[1], ps[2]:
        runner = CliRunner()
        result = runner.invoke(weigh_command, BASE_ARGS + ["--rule", "badformat"])
    assert result.exit_code == 1
    assert "Invalid rule" in result.output
