"""Drift detection: compare current Vault state against a saved snapshot."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List

from vaultdiff.differ import SecretDiff, VaultDiffer
from vaultdiff.snapshot import Snapshot, SnapshotEntry


@dataclass
class DriftEntry:
    path: str
    added_keys: List[str] = field(default_factory=list)
    removed_keys: List[str] = field(default_factory=list)
    changed_keys: List[str] = field(default_factory=list)

    @property
    def has_drift(self) -> bool:
        return bool(self.added_keys or self.removed_keys or self.changed_keys)

    def to_dict(self) -> dict:
        return {
            "path": self.path,
            "added_keys": self.added_keys,
            "removed_keys": self.removed_keys,
            "changed_keys": self.changed_keys,
        }


def detect_drift(snapshot: Snapshot, differ: VaultDiffer, mount: str = "secret") -> List[DriftEntry]:
    """Compare every path recorded in *snapshot* against the live Vault instance
    attached to *differ*'s right client."""
    entries: List[DriftEntry] = []

    for snap_entry in snapshot.entries:
        path = snap_entry.path
        try:
            live_data = differ.right_client.read_secret(path, mount=mount) or {}
        except Exception:
            live_data = {}

        baseline_data = snap_entry.data or {}
        all_keys = set(baseline_data) | set(live_data)

        drift = DriftEntry(path=path)
        for key in all_keys:
            if key not in baseline_data:
                drift.added_keys.append(key)
            elif key not in live_data:
                drift.removed_keys.append(key)
            elif baseline_data[key] != live_data[key]:
                drift.changed_keys.append(key)

        entries.append(drift)

    return entries
