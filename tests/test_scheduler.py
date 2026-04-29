"""Tests for vaultdiff.scheduler."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from vaultdiff.scheduler import RunResult, ScheduleConfig, Scheduler


def _make_diff(has_diff: bool) -> MagicMock:
    diff = MagicMock()
    diff.has_differences.return_value = has_diff
    return diff


def _noop_sleep(_seconds: float) -> None:
    pass


def test_run_result_to_dict():
    r = RunResult(path="secret/a", run_index=0, has_differences=True, timestamp=1234.0)
    d = r.to_dict()
    assert d["path"] == "secret/a"
    assert d["has_differences"] is True
    assert d["run_index"] == 0
    assert d["timestamp"] == 1234.0


def test_single_run_no_differences():
    diff_fn = MagicMock(return_value=_make_diff(False))
    config = ScheduleConfig(paths=["secret/a"], max_runs=1)
    scheduler = Scheduler(config, diff_fn)
    results = scheduler.run(sleep_fn=_noop_sleep)
    assert len(results) == 1
    assert results[0].has_differences is False
    assert results[0].error is None


def test_single_run_with_differences_triggers_callback():
    on_diff = MagicMock()
    diff_fn = MagicMock(return_value=_make_diff(True))
    config = ScheduleConfig(paths=["secret/b"], max_runs=1, on_diff=on_diff)
    scheduler = Scheduler(config, diff_fn)
    scheduler.run(sleep_fn=_noop_sleep)
    on_diff.assert_called_once()
    call_path = on_diff.call_args[0][0]
    assert call_path == "secret/b"


def test_multiple_runs_accumulate_results():
    diff_fn = MagicMock(return_value=_make_diff(False))
    config = ScheduleConfig(paths=["secret/a", "secret/b"], max_runs=2)
    scheduler = Scheduler(config, diff_fn)
    results = scheduler.run(sleep_fn=_noop_sleep)
    assert len(results) == 4  # 2 paths * 2 runs


def test_error_in_diff_fn_captured():
    on_error = MagicMock()

    def boom(_path: str):
        raise RuntimeError("vault unavailable")

    config = ScheduleConfig(paths=["secret/x"], max_runs=1, on_error=on_error)
    scheduler = Scheduler(config, boom)
    results = scheduler.run(sleep_fn=_noop_sleep)
    assert len(results) == 1
    assert results[0].error == "vault unavailable"
    assert results[0].has_differences is False
    on_error.assert_called_once()


def test_stop_prevents_further_runs():
    call_count = 0

    def diff_fn(_path: str):
        nonlocal call_count
        call_count += 1
        return _make_diff(False)

    config = ScheduleConfig(paths=["secret/a"], max_runs=5)
    scheduler = Scheduler(config, diff_fn)

    def stopping_sleep(_seconds: float) -> None:
        scheduler.stop()

    scheduler.run(sleep_fn=stopping_sleep)
    assert call_count == 1


def test_sleep_called_between_runs():
    sleep_mock = MagicMock()
    diff_fn = MagicMock(return_value=_make_diff(False))
    config = ScheduleConfig(paths=["secret/a"], max_runs=3, interval_seconds=60)
    scheduler = Scheduler(config, diff_fn)
    scheduler.run(sleep_fn=sleep_mock)
    assert sleep_mock.call_count == 2
    sleep_mock.assert_called_with(60)
