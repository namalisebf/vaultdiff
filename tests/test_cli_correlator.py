"""Tests for vaultdiff.cli_correlator."""
from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

from click.testing import CliRunner

from vaultdiff.cli_correlator import correlate_command
from vaultdiff.correlator import CorrelationReport, CorrelatedPath, CorrelatedKey
from vaultdiff.vault_client import VaultClientError


def _clean_report() -> CorrelationReport:
    return CorrelationReport(paths=[])


def _report_with_change() -> CorrelationReport:
    ck = CorrelatedKey(key="DB_PASS", environments_changed=["prod"], environments_clean=[])
    cp = CorrelatedPath(path="secret/app", keys=[ck])
    return CorrelationReport(paths=[cp])


def _patch_deps(report: CorrelationReport):
    return patch.multiple(
        "vaultdiff.cli_correlator",
        VaultClient=MagicMock(),
        VaultDiffer=MagicMock(),
        correlate_diffs=MagicMock(return_value=report),
    )


def test_correlate_text_output_no_changes():
    runner = CliRunner()
    with _patch_deps(_clean_report()):
        result = runner.invoke(correlate_command, [
            "--env", "prod=http://vault:8200",
            "--token", "prod=s.abc",
            "--path", "secret/app",
        ])
    assert result.exit_code == 0


def test_correlate_text_output_with_change():
    runner = CliRunner()
    with _patch_deps(_report_with_change()):
        result = runner.invoke(correlate_command, [
            "--env", "prod=http://vault:8200",
            "--token", "prod=s.abc",
            "--path", "secret/app",
        ])
    assert result.exit_code == 0
    assert "secret/app" in result.output
    assert "DB_PASS" in result.output
    assert "prod" in result.output


def test_correlate_json_output():
    runner = CliRunner()
    with _patch_deps(_report_with_change()):
        result = runner.invoke(correlate_command, [
            "--env", "prod=http://vault:8200",
            "--token", "prod=s.abc",
            "--path", "secret/app",
            "--format", "json",
        ])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert "paths" in data
    assert "total_paths" in data


def test_correlate_vault_client_error_exits_1():
    runner = CliRunner()
    with patch("vaultdiff.cli_correlator.VaultClient",
               side_effect=VaultClientError("bad token")):
        result = runner.invoke(correlate_command, [
            "--env", "prod=http://vault:8200",
            "--token", "prod=s.abc",
            "--path", "secret/app",
        ])
    assert result.exit_code == 1
    assert "Vault error" in result.output


def test_correlate_bad_env_format_exits_1():
    runner = CliRunner()
    result = runner.invoke(correlate_command, [
        "--env", "badformat",
        "--token", "prod=s.abc",
        "--path", "secret/app",
    ])
    assert result.exit_code == 1


def test_correlate_universal_only_flag_filters_output():
    runner = CliRunner()
    ck_universal = CorrelatedKey(
        key="SHARED",
        environments_changed=["prod", "staging"],
        environments_clean=[],
    )
    ck_partial = CorrelatedKey(
        key="LOCAL",
        environments_changed=["prod"],
        environments_clean=["staging"],
    )
    cp = CorrelatedPath(path="secret/app", keys=[ck_universal, ck_partial])
    report = CorrelationReport(paths=[cp])
    with _patch_deps(report):
        result = runner.invoke(correlate_command, [
            "--env", "prod=http://vault:8200",
            "--env", "staging=http://vault2:8200",
            "--token", "prod=s.abc",
            "--token", "staging=s.xyz",
            "--path", "secret/app",
            "--universal-only",
        ])
    assert result.exit_code == 0
    assert "SHARED" in result.output
    assert "LOCAL" not in result.output
