"""Stream secret diffs path-by-path with optional callback support."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Iterable, Iterator, List, Optional

from vaultdiff.differ import SecretDiff, VaultDiffer
from vaultdiff.vault_client import VaultClient


@dataclass
class StreamConfig:
    paths: List[str] = field(default_factory=list)
    stop_on_error: bool = False
    only_differences: bool = False

    @classmethod
    def from_dict(cls, data: dict) -> "StreamConfig":
        return cls(
            paths=data.get("paths", []),
            stop_on_error=bool(data.get("stop_on_error", False)),
            only_differences=bool(data.get("only_differences", False)),
        )


@dataclass
class StreamEvent:
    path: str
    diff: Optional[SecretDiff]
    error: Optional[str] = None

    @property
    def has_error(self) -> bool:
        return self.error is not None

    def to_dict(self) -> dict:
        return {
            "path": self.path,
            "diff": {
                "changed": list(self.diff.changed_keys) if self.diff else [],
                "only_in_left": list(self.diff.only_in_left) if self.diff else [],
                "only_in_right": list(self.diff.only_in_right) if self.diff else [],
                "has_differences": self.diff.has_differences if self.diff else False,
            } if not self.has_error else None,
            "error": self.error,
        }


class Streamer:
    def __init__(
        self,
        left: VaultClient,
        right: VaultClient,
        config: StreamConfig,
        on_event: Optional[Callable[[StreamEvent], None]] = None,
    ) -> None:
        self._left = left
        self._right = right
        self._config = config
        self._on_event = on_event
        self._differ = VaultDiffer(left, right)

    def stream(self, paths: Optional[Iterable[str]] = None) -> Iterator[StreamEvent]:
        targets = list(paths) if paths is not None else self._config.paths
        for path in targets:
            event = self._process(path)
            if event is None:
                continue
            if self._on_event:
                self._on_event(event)
            yield event
            if event.has_error and self._config.stop_on_error:
                return

    def _process(self, path: str) -> Optional[StreamEvent]:
        try:
            diff = self._differ.diff_secret(path, path)
        except Exception as exc:  # noqa: BLE001
            return StreamEvent(path=path, diff=None, error=str(exc))
        if self._config.only_differences and not diff.has_differences:
            return None
        return StreamEvent(path=path, diff=diff)
