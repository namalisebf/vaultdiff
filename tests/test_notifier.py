"""Tests for vaultdiff.notifier."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from vaultdiff.notifier import Notifier, NotifierConfig, NotifierError


def _make_entry(has_differences: bool = True, path: str = "secret/app"):
    entry = MagicMock()
    entry.has_differences = has_differences
    entry.to_dict.return_value = {"path": path, "has_differences": has_differences}
    return entry


def _make_mock_response(status: int = 200):
    resp = MagicMock()
    resp.status = status
    resp.__enter__ = lambda s: s
    resp.__exit__ = MagicMock(return_value=False)
    return resp


def test_send_skips_when_no_url():
    config = NotifierConfig(webhook_url=None)
    notifier = Notifier(config)
    # Should not raise even with entries
    notifier.send([_make_entry()])


def test_send_skips_when_only_on_differences_and_no_diffs():
    config = NotifierConfig(webhook_url="http://example.com/hook", only_on_differences=True)
    notifier = Notifier(config)
    with patch("urllib.request.urlopen") as mock_open:
        notifier.send([_make_entry(has_differences=False)])
        mock_open.assert_not_called()


def test_send_dispatches_when_differences_present():
    config = NotifierConfig(webhook_url="http://example.com/hook")
    notifier = Notifier(config)
    with patch("urllib.request.urlopen", return_value=_make_mock_response(200)) as mock_open:
        notifier.send([_make_entry(has_differences=True)])
        mock_open.assert_called_once()


def test_send_includes_slack_channel_in_payload():
    config = NotifierConfig(
        webhook_url="http://example.com/hook",
        slack_channel="#alerts",
    )
    notifier = Notifier(config)
    captured = {}

    def fake_urlopen(req, timeout=None):
        import json
        captured["payload"] = json.loads(req.data.decode())
        return _make_mock_response(200)

    with patch("urllib.request.urlopen", side_effect=fake_urlopen):
        notifier.send([_make_entry()])

    assert captured["payload"]["channel"] == "#alerts"
    assert "text" in captured["payload"]


def test_send_raises_notifier_error_on_http_error():
    config = NotifierConfig(webhook_url="http://example.com/hook")
    notifier = Notifier(config)
    with patch("urllib.request.urlopen", return_value=_make_mock_response(500)):
        with pytest.raises(NotifierError, match="HTTP 500"):
            notifier.send([_make_entry()])


def test_send_raises_notifier_error_on_network_failure():
    config = NotifierConfig(webhook_url="http://example.com/hook")
    notifier = Notifier(config)
    with patch("urllib.request.urlopen", side_effect=OSError("connection refused")):
        with pytest.raises(NotifierError, match="Failed to send notification"):
            notifier.send([_make_entry()])


def test_send_without_only_on_differences_sends_always():
    config = NotifierConfig(
        webhook_url="http://example.com/hook",
        only_on_differences=False,
    )
    notifier = Notifier(config)
    with patch("urllib.request.urlopen", return_value=_make_mock_response(200)) as mock_open:
        notifier.send([_make_entry(has_differences=False)])
        mock_open.assert_called_once()
