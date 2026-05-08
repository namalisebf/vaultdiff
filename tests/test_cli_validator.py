"""Tests for the validate CLI command."""
from __future__ import annotations

import json
from contextlib import contextmanager
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from vaultdiff.cli_validator import validate_command
from vaultdiff.differ import SecretDiff
from vaultdiff.validator import ValidationViolation
from vaultdiff.vault_client import VaultClientError

_CLEAN_DIFF = SecretDiff(path="secret/app", changed={}, only_in_left={}, only_in_right={})
_DIRTY_DIFF = SecretDiff(
    path="secret/app",
    changed={"key": ("a", "b")},
    only_in_left={},
    only_in_right={},
)


@contextmanager
def _patch_deps(diff=_CLEAN_DIFF, violations=None):
    if violations is None:
        violations = []
    with patch("vaultdiff.cli_validator.VaultClient") as mock_vc, \
         patch("vaultdiff.cli_validator.VaultDiffer") as mock_differ, \
         patch("vaultdiff.cli_validator.Validator") as mock_validator:
        mock_differ_inst = MagicMock()
        mock_differ_inst.diff_secret.return_value = diff
        mock_differ.return_value = mock_differ_inst

        mock_validator_inst = MagicMock()
        mock_validator_inst.validate.return_value = violations
        mock_validator.return_value = mock_validator_inst

        yield mock_vc, mock_differ_inst, mock_validator_inst


def _base_args(fmt="text"):
    return [
        "--left-addr", "http://left",
        "--left-token", "tok-l",
        "--right-addr", "http://right",
        "--right-token", "tok-r",
        "--path", "secret/app",
        "--format", fmt,
    ]


def test_validate_clean_text_output():
    with _patch_deps() as (_, __, ___):
        runner = CliRunner()
        result = runner.invoke(validate_command, _base_args())
    assert result.exit_code == 0
    assert "passed" in result.output


def test_validate_violation_text_output():
    v = ValidationViolation(path="secret/app", rule_glob="secret/*", message="Missing key 'token'")
    with _patch_deps(violations=[v]) as (_, __, ___):
        runner = CliRunner()
        result = runner.invoke(validate_command, _base_args())
    assert result.exit_code == 0
    assert "Missing key" in result.output


def test_validate_exit_code_on_violations():
    v = ValidationViolation(path="secret/app", rule_glob="secret/*", message="Missing key 'token'")
    with _patch_deps(violations=[v]) as (_, __, ___):
        runner = CliRunner()
        result = runner.invoke(validate_command, _base_args() + ["--exit-code"])
    assert result.exit_code == 1


def test_validate_json_output():
    v = ValidationViolation(path="secret/app", rule_glob="secret/*", message="Forbidden key 'debug'")
    with _patch_deps(violations=[v]) as (_, __, ___):
        runner = CliRunner()
        result = runner.invoke(validate_command, _base_args(fmt="json"))
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert isinstance(data, list)
    assert data[0]["path"] == "secret/app"


def test_validate_vault_client_error_exits_1():
    with patch("vaultdiff.cli_validator.VaultClient", side_effect=VaultClientError("bad")):
        runner = CliRunner()
        result = runner.invoke(validate_command, _base_args())
    assert result.exit_code == 1
    assert "Error" in result.output
