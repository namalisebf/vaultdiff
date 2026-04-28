"""Integration-style tests for Notifier payload structure."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from vaultdiff.notifier import Notifier, NotifierConfig


def _make_entry(path: str, has_differences: bool, changed: dict | None = None):
    entry = MagicMock()
    entry.has_differences = has_differences
    entry.to_dict.return_value = {
        "path": path,
        "has_differences": has_differences,
        "changed_keys": changed or {},
    }
    return entry


def _capture_request_body(requests_captured: list):
    def fake_urlopen(req, timeout=None):
        requests_captured.append(json.loads(req.data.decode()))
        resp = MagicMock()
        resp.status = 200
        resp.__enter__ = lambda s: s
        resp.__exit__ = MagicMock(return_value=False)
        return resp
    return fake_urlopen


def test_payload_contains_all_entries():
    config = NotifierConfig(webhook_url="http://hook.example.com", only_on_differences=False)
    notifier = Notifier(config)
    entries = [
        _make_entry("secret/a", True, {"key": ("old", "new")}),
        _make_entry("secret/b", False),
    ]
    captured: list = []
    with patch("urllib.request.urlopen", side_effect=_capture_request_body(captured)):
        notifier.send(entries)

    assert len(captured) == 1
    payload = captured[0]
    assert len(payload["vaultdiff_audit"]) == 2
    assert payload["vaultdiff_audit"][0]["path"] == "secret/a"


def test_extra_headers_forwarded():
    config = NotifierConfig(
        webhook_url="http://hook.example.com",
        extra_headers={"X-Api-Key": "secret123"},
    )
    notifier = Notifier(config)
    header_captured: list = []

    def fake_urlopen(req, timeout=None):
        header_captured.append(dict(req.headers))
        resp = MagicMock()
        resp.status = 200
        resp.__enter__ = lambda s: s
        resp.__exit__ = MagicMock(return_value=False)
        return resp

    with patch("urllib.request.urlopen", side_effect=fake_urlopen):
        notifier.send([_make_entry("secret/a", True)])

    assert header_captured[0].get("X-api-key") == "secret123"


def test_no_request_when_entries_empty_and_only_on_differences():
    config = NotifierConfig(webhook_url="http://hook.example.com", only_on_differences=True)
    notifier = Notifier(config)
    with patch("urllib.request.urlopen") as mock_open:
        notifier.send([])
        mock_open.assert_not_called()
