"""Snapshot module: capture and compare full Vault path trees at a point in time."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional


@dataclass
class SnapshotEntry:
    path: str
    keys: List[str]
    captured_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict:
        return {
            "path": self.path,
            "keys": sorted(self.keys),
            "captured_at": self.captured_at,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "SnapshotEntry":
        return cls(
            path=data["path"],
            keys=data["keys"],
            captured_at=data["captured_at"],
        )


@dataclass
class Snapshot:
    label: str
    entries: List[SnapshotEntry] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict:
        return {
            "label": self.label,
            "created_at": self.created_at,
            "entries": [e.to_dict() for e in self.entries],
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Snapshot":
        entries = [SnapshotEntry.from_dict(e) for e in data.get("entries", [])]
        snap = cls(label=data["label"], entries=entries)
        snap.created_at = data["created_at"]
        return snap


def save_snapshot(snapshot: Snapshot, filepath: str) -> None:
    path = Path(filepath)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        json.dump(snapshot.to_dict(), fh, indent=2)


def load_snapshot(filepath: str) -> Snapshot:
    path = Path(filepath)
    if not path.exists():
        raise FileNotFoundError(f"Snapshot file not found: {filepath}")
    with path.open("r", encoding="utf-8") as fh:
        data = json.load(fh)
    return Snapshot.from_dict(data)


def diff_snapshots(old: Snapshot, new: Snapshot) -> Dict[str, dict]:
    """Return a mapping of path -> change description between two snapshots."""
    old_map = {e.path: set(e.keys) for e in old.entries}
    new_map = {e.path: set(e.keys) for e in new.entries}

    all_paths = old_map.keys() | new_map.keys()
    result = {}

    for path in sorted(all_paths):
        if path not in old_map:
            result[path] = {"status": "added", "keys_added": sorted(new_map[path]), "keys_removed": []}
        elif path not in new_map:
            result[path] = {"status": "removed", "keys_added": [], "keys_removed": sorted(old_map[path])}
        else:
            added = sorted(new_map[path] - old_map[path])
            removed = sorted(old_map[path] - new_map[path])
            if added or removed:
                result[path] = {"status": "changed", "keys_added": added, "keys_removed": removed}

    return result
