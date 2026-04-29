"""Watchdog module: monitors Vault paths for unexpected changes and raises alerts."""
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional

from vaultdiff.differ import SecretDiff, VaultDiffer
from vaultdiff.snapshot import Snapshot, SnapshotEntry
from vaultdiff.drift import DriftEntry, detect_drift


@dataclass
class WatchEvent:
    path: str
    drift_entries: List[DriftEntry]

    def has_changes(self) -> bool:
        return any(e.has_drift() for e in self.drift_entries)

    def to_dict(self) -> dict:
        return {
            "path": self.path,
            "changes": [e.to_dict() for e in self.drift_entries if e.has_drift()],
        }


@dataclass
class WatchdogConfig:
    paths: List[str]
    baseline_snapshot: Snapshot
    on_change: Optional[Callable[[WatchEvent], None]] = None
    on_error: Optional[Callable[[str, Exception], None]] = None


class Watchdog:
    def __init__(self, config: WatchdogConfig, differ: VaultDiffer) -> None:
        self._config = config
        self._differ = differ

    def check_path(self, path: str) -> WatchEvent:
        baseline = self._config.baseline_snapshot
        current_data = self._differ.client_left.read_secret(path)
        baseline_entry = baseline.get(path)
        baseline_data: Dict[str, str] = baseline_entry.data if baseline_entry else {}
        drift_entries = detect_drift(path, baseline_data, current_data or {})
        return WatchEvent(path=path, drift_entries=drift_entries)

    def run_once(self) -> List[WatchEvent]:
        events: List[WatchEvent] = []
        for path in self._config.paths:
            try:
                event = self.check_path(path)
                if event.has_changes() and self._config.on_change:
                    self._config.on_change(event)
                events.append(event)
            except Exception as exc:  # noqa: BLE001
                if self._config.on_error:
                    self._config.on_error(path, exc)
        return events
