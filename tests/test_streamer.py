"""Unit tests for vaultdiff.streamer."""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from vaultdiff.differ import SecretDiff
from vaultdiff.streamer import StreamConfig, StreamEvent, Streamer


def _make_diff(changed=(), left=(), right=()) -> SecretDiff:
    return SecretDiff(
        changed_keys=set(changed),
        only_in_left=set(left),
        only_in_right=set(right),
    )


def _make_streamer(diffs: dict, only_differences=False, stop_on_error=False):
    left = MagicMock()
    right = MagicMock()
    config = StreamConfig(
        paths=list(diffs.keys()),
        only_differences=only_differences,
        stop_on_error=stop_on_error,
    )
    streamer = Streamer(left=left, right=right, config=config)

    def fake_diff(lpath, rpath):
        if lpath in diffs:
            result = diffs[lpath]
            if isinstance(result, Exception):
                raise result
            return result
        return _make_diff()

    streamer._differ = MagicMock()
    streamer._differ.diff_secret.side_effect = fake_diff
    return streamer


def test_stream_yields_event_for_each_path():
    diffs = {"secret/a": _make_diff(), "secret/b": _make_diff(changed=["key"])}
    streamer = _make_streamer(diffs)
    events = list(streamer.stream())
    assert len(events) == 2
    assert events[0].path == "secret/a"
    assert events[1].path == "secret/b"


def test_stream_event_has_no_error_on_success():
    streamer = _make_streamer({"secret/x": _make_diff()})
    events = list(streamer.stream())
    assert not events[0].has_error
    assert events[0].diff is not None


def test_stream_event_captures_exception_as_error():
    streamer = _make_streamer({"secret/bad": RuntimeError("boom")})
    events = list(streamer.stream())
    assert events[0].has_error
    assert "boom" in events[0].error
    assert events[0].diff is None


def test_only_differences_skips_clean_paths():
    diffs = {"secret/clean": _make_diff(), "secret/dirty": _make_diff(changed=["k"])}
    streamer = _make_streamer(diffs, only_differences=True)
    events = list(streamer.stream())
    assert len(events) == 1
    assert events[0].path == "secret/dirty"


def test_stop_on_error_halts_iteration():
    diffs = {
        "secret/first": RuntimeError("fail"),
        "secret/second": _make_diff(),
    }
    streamer = _make_streamer(diffs, stop_on_error=True)
    events = list(streamer.stream())
    assert len(events) == 1
    assert events[0].has_error


def test_on_event_callback_is_called():
    calls = []
    diffs = {"secret/a": _make_diff(changed=["x"])}
    streamer = _make_streamer(diffs)
    streamer._on_event = calls.append
    list(streamer.stream())
    assert len(calls) == 1
    assert calls[0].path == "secret/a"


def test_stream_event_to_dict_structure():
    diff = _make_diff(changed=["k"], left=["l"], right=["r"])
    event = StreamEvent(path="secret/p", diff=diff)
    d = event.to_dict()
    assert d["path"] == "secret/p"
    assert d["error"] is None
    assert "k" in d["diff"]["changed"]
    assert "l" in d["diff"]["only_in_left"]
    assert "r" in d["diff"]["only_in_right"]
    assert d["diff"]["has_differences"] is True


def test_stream_event_to_dict_on_error():
    event = StreamEvent(path="secret/bad", diff=None, error="oops")
    d = event.to_dict()
    assert d["error"] == "oops"
    assert d["diff"] is None


def test_stream_config_from_dict():
    cfg = StreamConfig.from_dict({"paths": ["a", "b"], "only_differences": True})
    assert cfg.paths == ["a", "b"]
    assert cfg.only_differences is True
    assert cfg.stop_on_error is False
