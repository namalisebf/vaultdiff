"""Tests for vaultdiff.cli_notify."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from vaultdiff.cli_notify import notify_command
from vaultdiff.notifier import NotifierError
from vaultdiff.vault_client import VaultClientError

BASE_ARGS = [
    "--left-addr", "http://left:8200",
    "--left-token", "tok-left",
    "--right-addr", "http://right:8200",
    "--right-token", "tok-right",
    "--webhook-url", "http://hook.example.com",
    "secret/app",
]


def _patch_deps(diff=None, notifier_error=None):
    if diff is None:
        diff = MagicMock(changed_keys={}, only_in_left={}, only_in_right={})

    patches = [
        patch("vaultdiff.cli_notify.VaultClient"),
        patch("vaultdiff.cli_notify.VaultDiffer"),
        patch("vaultdiff.cli_notify.Auditor"),
        patch("vaultdiff.cli_notify.Notifier"),
    ]
    return patches, diff, notifier_error


def test_notify_success():
    runner = CliRunner()
    with patch("vaultdiff.cli_notify.VaultClient"), \
         patch("vaultdiff.cli_notify.VaultDiffer") as MockDiffer, \
         patch("vaultdiff.cli_notify.Auditor") as MockAuditor, \
         patch("vaultdiff.cli_notify.Notifier") as MockNotifier:

        diff = MagicMock()
        MockDiffer.return_value.diff_secret.return_value = diff
        MockAuditor.return_value.entries = [MagicMock()]
        MockNotifier.return_value.send.return_value = None

        result = runner.invoke(notify_command, BASE_ARGS)

    assert result.exit_code == 0
    assert "Notification dispatched" in result.output


def test_notify_vault_client_error():
    runner = CliRunner()
    with patch("vaultdiff.cli_notify.VaultClient", side_effect=VaultClientError("bad token")):
        result = runner.invoke(notify_command, BASE_ARGS)
    assert result.exit_code != 0
    assert "bad token" in result.output


def test_notify_notifier_error():
    runner = CliRunner()
    with patch("vaultdiff.cli_notify.VaultClient"), \
         patch("vaultdiff.cli_notify.VaultDiffer") as MockDiffer, \
         patch("vaultdiff.cli_notify.Auditor") as MockAuditor, \
         patch("vaultdiff.cli_notify.Notifier") as MockNotifier:

        MockDiffer.return_value.diff_secret.return_value = MagicMock()
        MockAuditor.return_value.entries = []
        MockNotifier.return_value.send.side_effect = NotifierError("timeout")

        result = runner.invoke(notify_command, BASE_ARGS)

    assert result.exit_code != 0
    assert "timeout" in result.output


def test_notify_always_flag_sets_config():
    runner = CliRunner()
    captured_config = {}

    def fake_notifier(config):
        captured_config["only_on_differences"] = config.only_on_differences
        m = MagicMock()
        m.send.return_value = None
        return m

    with patch("vaultdiff.cli_notify.VaultClient"), \
         patch("vaultdiff.cli_notify.VaultDiffer") as MockDiffer, \
         patch("vaultdiff.cli_notify.Auditor") as MockAuditor, \
         patch("vaultdiff.cli_notify.Notifier", side_effect=fake_notifier):

        MockDiffer.return_value.diff_secret.return_value = MagicMock()
        MockAuditor.return_value.entries = []

        runner.invoke(notify_command, BASE_ARGS + ["--always"])

    assert captured_config.get("only_on_differences") is False
