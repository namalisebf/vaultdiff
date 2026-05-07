"""Tests for vaultdiff.throttler."""
import pytest
from unittest.mock import MagicMock

from vaultdiff.throttler import ThrottleConfig, ThrottleStats, Throttler


# ---------------------------------------------------------------------------
# ThrottleConfig
# ---------------------------------------------------------------------------

def test_throttle_config_defaults():
    cfg = ThrottleConfig()
    assert cfg.max_calls_per_second == 10.0
    assert cfg.burst == 1
    assert cfg.enabled is True


def test_throttle_config_from_dict():
    cfg = ThrottleConfig.from_dict({"max_calls_per_second": 5, "burst": 3, "enabled": False})
    assert cfg.max_calls_per_second == 5.0
    assert cfg.burst == 3
    assert cfg.enabled is False


def test_throttle_config_from_dict_empty():
    cfg = ThrottleConfig.from_dict({})
    assert cfg.max_calls_per_second == 10.0
    assert cfg.burst == 1
    assert cfg.enabled is True


# ---------------------------------------------------------------------------
# ThrottleStats
# ---------------------------------------------------------------------------

def test_throttle_stats_to_dict():
    stats = ThrottleStats(total_calls=5, total_wait_seconds=0.12345, throttled_calls=2)
    d = stats.to_dict()
    assert d["total_calls"] == 5
    assert d["total_wait_seconds"] == 0.1235
    assert d["throttled_calls"] == 2


# ---------------------------------------------------------------------------
# Throttler – disabled
# ---------------------------------------------------------------------------

def test_throttler_disabled_never_sleeps():
    sleep = MagicMock()
    cfg = ThrottleConfig(enabled=False)
    t = Throttler(cfg, _sleep=sleep)
    for _ in range(20):
        t.acquire()
    sleep.assert_not_called()
    assert t.stats.total_calls == 20
    assert t.stats.throttled_calls == 0


# ---------------------------------------------------------------------------
# Throttler – enabled, burst absorbs first call
# ---------------------------------------------------------------------------

def test_throttler_first_call_no_sleep_when_burst_available():
    sleep = MagicMock()
    now_values = iter([0.0, 0.0])
    cfg = ThrottleConfig(max_calls_per_second=1.0, burst=1)
    t = Throttler(cfg, _sleep=sleep, _now=lambda: next(now_values))
    t.acquire()
    sleep.assert_not_called()
    assert t.stats.throttled_calls == 0


def test_throttler_second_call_sleeps_when_no_burst():
    sleep = MagicMock()
    clock = [0.0]

    def _now():
        return clock[0]

    cfg = ThrottleConfig(max_calls_per_second=2.0, burst=1)
    t = Throttler(cfg, _sleep=sleep, _now=_now)

    # First call consumes the burst token
    t.acquire()
    sleep.assert_not_called()

    # Second call: no time has passed, tokens < 1 → must sleep
    t.acquire()
    sleep.assert_called_once()
    wait_arg = sleep.call_args[0][0]
    assert wait_arg > 0
    assert t.stats.throttled_calls == 1


def test_throttler_refill_after_elapsed_time_avoids_sleep():
    sleep = MagicMock()
    clock = [0.0]

    def _now():
        return clock[0]

    cfg = ThrottleConfig(max_calls_per_second=2.0, burst=1)
    t = Throttler(cfg, _sleep=sleep, _now=_now)

    t.acquire()  # consume burst
    clock[0] = 1.0  # 1 second passes → 2 new tokens refilled, capped at burst=1
    t.acquire()  # should NOT sleep
    sleep.assert_not_called()
    assert t.stats.throttled_calls == 0
    assert t.stats.total_calls == 2
