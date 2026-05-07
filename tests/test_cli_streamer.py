"""Tests for vaultdiff.cli_streamer."""
from __future__ import annotations

from contextlib import contextmanager
from unittest.mock import MagicMock, patch

from click.testing import CliRunner

from vaultdiff.cli_streamer import stream_command
from vaultdiff.differ import SecretDiff
from vaultdiff.streamer import StreamEvent
from vaultdiff.vault_client import VaultClientError


def _make_diff(changed=(), left=(), right=()) -> SecretDiff:
    return SecretDiff(
        changed_keys=set(changed),
        only_in_left=set(left),
        only_in_right=set(right),
    )


@contextmanager
 def _patch_deps(events):
    with patch("vaultdiff.cli_streamer.VaultClient") as mock_vc, \
         patch("vaultdiff.cli_streamer.Streamer") as mock_streamer_cls:
        mock_streamer = MagicMock()
        mock_streamer.stream.return_value = iter(events)
        mock_streamer_cls.return_value = mock_streamer
        yield mock_vc, mock_streamer_cls


_BASE_ARGS = [
    "--left-addr", "http://left",
    "--left-token", "tok-l",
    "--right-addr", "http://right",
    "--right-token", "tok-r",
    "--path", "secret/a",
]


def test_stream_clean_text_output():
    events = [StreamEvent(path="secret/a", diff=_make_diff())]
    with _patch_deps(events):
        result = CliRunner().invoke(stream_command, _BASE_ARGS)
    assert result.exit_code == 0
    assert "[CLEAN] secret/a" in result.output


def test_stream_changed_text_output():
    diff = _make_diff(changed=["token"])
    events = [StreamEvent(path="secret/a", diff=diff)]
    with _patch_deps(events):
        result = CliRunner().invoke(stream_command, _BASE_ARGS)
    assert "[CHANGED] secret/a" in result.output
    assert "~ token" in result.output


def test_stream_json_output():
    diff = _make_diff(changed=["k"])
    events = [StreamEvent(path="secret/a", diff=diff)]
    with _patch_deps(events):
        result = CliRunner().invoke(stream_command, _BASE_ARGS + ["--format", "json"])
    assert result.exit_code == 0
    assert '"path": "secret/a"' in result.output


def test_stream_exit_code_on_differences():
    diff = _make_diff(changed=["k"])
    events = [StreamEvent(path="secret/a", diff=diff)]
    with _patch_deps(events):
        result = CliRunner().invoke(stream_command, _BASE_ARGS + ["--exit-code"])
    assert result.exit_code == 2


def test_stream_vault_client_error_exits_1():
    with patch("vaultdiff.cli_streamer.VaultClient", side_effect=VaultClientError("bad")):
        result = CliRunner().invoke(stream_command, _BASE_ARGS)
    assert result.exit_code == 1


def test_stream_error_event_exits_1():
    events = [StreamEvent(path="secret/a", diff=None, error="boom")]
    with _patch_deps(events):
        result = CliRunner().invoke(stream_command, _BASE_ARGS)
    assert result.exit_code == 1
