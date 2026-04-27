"""Tests for vaultdiff.cli_baseline commands."""

import json
import os
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from vaultdiff.baseline import BaselineEntry
from vaultdiff.cli_baseline import baseline_command
from vaultdiff.differ import SecretDiff
from vaultdiff.vault_client import VaultClientError

_COMMON_ARGS = [
    "--left-addr", "http://left:8200",
    "--right-addr", "http://right:8200",
    "--left-token", "tok-left",
    "--right-token", "tok-right",
    "--path", "secret/app",
]

_NO_DIFF = SecretDiff(changed_keys={}, only_in_left=[], only_in_right=[])
_WITH_DIFF = SecretDiff(
    changed_keys={"KEY": ("old", "new")}, only_in_left=[], only_in_right=[]
)


def _patch_deps(differ_diffs: dict):
    differ_mock = MagicMock()
    differ_mock.diff_secret.side_effect = lambda p: differ_diffs.get(p, _NO_DIFF)
    differ_mock.diff_recursive.side_effect = lambda p: differ_diffs
    return patch("vaultdiff.cli_baseline.VaultClient"), patch(
        "vaultdiff.cli_baseline.VaultDiffer", return_value=differ_mock
    )


def test_save_creates_baseline_file(tmp_path):
    output = str(tmp_path / "baseline.json")
    patch_client, patch_differ = _patch_deps({"secret/app": _WITH_DIFF})
    with patch_client, patch_differ:
        runner = CliRunner()
        result = runner.invoke(
            baseline_command, ["save"] + _COMMON_ARGS + ["--output", output]
        )
    assert result.exit_code == 0, result.output
    assert os.path.exists(output)
    with open(output) as fh:
        data = json.load(fh)
    assert data[0]["path"] == "secret/app"
    assert data[0]["changed_keys"] == ["KEY"]


def test_save_exits_on_vault_error():
    with patch("vaultdiff.cli_baseline.VaultClient", side_effect=VaultClientError("bad")):
        runner = CliRunner()
        result = runner.invoke(
            baseline_command,
            ["save"] + _COMMON_ARGS + ["--output", "/tmp/x.json"],
        )
    assert result.exit_code == 1
    assert "Error" in result.output


def test_check_no_regressions(tmp_path):
    baseline_file = str(tmp_path / "b.json")
    baseline = [BaselineEntry("secret/app", ["KEY"], [], [])]
    from vaultdiff.baseline import save_baseline
    save_baseline(baseline_file, baseline)

    patch_client, patch_differ = _patch_deps({"secret/app": _WITH_DIFF})
    with patch_client, patch_differ:
        runner = CliRunner()
        result = runner.invoke(
            baseline_command,
            ["check"] + _COMMON_ARGS + ["--baseline", baseline_file],
        )
    assert result.exit_code == 0
    assert "No regressions" in result.output


def test_check_detects_regression(tmp_path):
    baseline_file = str(tmp_path / "b.json")
    baseline = [BaselineEntry("secret/app", [], [], [])]
    from vaultdiff.baseline import save_baseline
    save_baseline(baseline_file, baseline)

    patch_client, patch_differ = _patch_deps({"secret/app": _WITH_DIFF})
    with patch_client, patch_differ:
        runner = CliRunner()
        result = runner.invoke(
            baseline_command,
            ["check"] + _COMMON_ARGS + ["--baseline", baseline_file],
        )
    assert result.exit_code == 1


def test_check_missing_baseline_file():
    patch_client, patch_differ = _patch_deps({})
    with patch_client, patch_differ:
        runner = CliRunner()
        result = runner.invoke(
            baseline_command,
            ["check"] + _COMMON_ARGS + ["--baseline", "/no/such/file.json"],
        )
    assert result.exit_code == 1
    assert "Error" in result.output
