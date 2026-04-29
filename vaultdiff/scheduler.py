"""Scheduled diff runner: periodically compares Vault paths and records results."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Callable, List, Optional


@dataclass
class ScheduleConfig:
    paths: List[str]
    interval_seconds: int = 300
    max_runs: Optional[int] = None
    on_diff: Optional[Callable[[str, object], None]] = None
    on_error: Optional[Callable[[str, Exception], None]] = None


@dataclass
class RunResult:
    path: str
    run_index: int
    has_differences: bool
    error: Optional[str] = None
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return {
            "path": self.path,
            "run_index": self.run_index,
            "has_differences": self.has_differences,
            "error": self.error,
            "timestamp": self.timestamp,
        }


class Scheduler:
    def __init__(self, config: ScheduleConfig, diff_fn: Callable[[str], object]) -> None:
        self._config = config
        self._diff_fn = diff_fn
        self._results: List[RunResult] = []
        self._stopped = False

    def stop(self) -> None:
        self._stopped = True

    def _run_once(self, run_index: int) -> List[RunResult]:
        results = []
        for path in self._config.paths:
            try:
                diff = self._diff_fn(path)
                has_diff = getattr(diff, "has_differences", lambda: False)()
                result = RunResult(path=path, run_index=run_index, has_differences=has_diff)
                if has_diff and self._config.on_diff:
                    self._config.on_diff(path, diff)
            except Exception as exc:  # noqa: BLE001
                result = RunResult(
                    path=path,
                    run_index=run_index,
                    has_differences=False,
                    error=str(exc),
                )
                if self._config.on_error:
                    self._config.on_error(path, exc)
            results.append(result)
        return results

    def run(self, sleep_fn: Callable[[float], None] = time.sleep) -> List[RunResult]:
        run_index = 0
        while not self._stopped:
            batch = self._run_once(run_index)
            self._results.extend(batch)
            run_index += 1
            if self._config.max_runs is not None and run_index >= self._config.max_runs:
                break
            if not self._stopped:
                sleep_fn(self._config.interval_seconds)
        return self._results

    @property
    def results(self) -> List[RunResult]:
        return list(self._results)
