"""Rate-limiting / throttle config for Vault API calls across diff operations."""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Callable, List, Optional


@dataclass
class ThrottleConfig:
    max_calls_per_second: float = 10.0
    burst: int = 1
    enabled: bool = True

    @classmethod
    def from_dict(cls, data: dict) -> "ThrottleConfig":
        return cls(
            max_calls_per_second=float(data.get("max_calls_per_second", 10.0)),
            burst=int(data.get("burst", 1)),
            enabled=bool(data.get("enabled", True)),
        )


@dataclass
class ThrottleStats:
    total_calls: int = 0
    total_wait_seconds: float = 0.0
    throttled_calls: int = 0

    def to_dict(self) -> dict:
        return {
            "total_calls": self.total_calls,
            "total_wait_seconds": round(self.total_wait_seconds, 4),
            "throttled_calls": self.throttled_calls,
        }


class Throttler:
    """Token-bucket throttler that rate-limits callable invocations."""

    def __init__(
        self,
        config: ThrottleConfig,
        _sleep: Callable[[float], None] = time.sleep,
        _now: Callable[[], float] = time.monotonic,
    ) -> None:
        self._config = config
        self._sleep = _sleep
        self._now = _now
        self._tokens: float = float(config.burst)
        self._last_refill: float = _now()
        self.stats = ThrottleStats()

    def _refill(self) -> None:
        now = self._now()
        elapsed = now - self._last_refill
        self._tokens = min(
            float(self._config.burst),
            self._tokens + elapsed * self._config.max_calls_per_second,
        )
        self._last_refill = now

    def acquire(self) -> None:
        """Block until a token is available, then consume it."""
        if not self._config.enabled:
            self.stats.total_calls += 1
            return

        self._refill()
        if self._tokens >= 1.0:
            self._tokens -= 1.0
            self.stats.total_calls += 1
            return

        # Need to wait for a token
        wait = (1.0 - self._tokens) / self._config.max_calls_per_second
        self._sleep(wait)
        self.stats.total_wait_seconds += wait
        self.stats.throttled_calls += 1
        self._tokens = 0.0
        self.stats.total_calls += 1
        self._last_refill = self._now()
