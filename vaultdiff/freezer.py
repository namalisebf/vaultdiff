"""Freezer: capture and compare point-in-time frozen states of secret diffs."""
from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

from vaultdiff.differ import SecretDiff


@dataclass
class FrozenEntry:
    path: str
    changed_keys: List[str]
    only_in_left: List[str]
    only_in_right: List[str]
    frozen_at: float = field(default_factory=time.time)

    def has_differences(self) -> bool:
        return bool(self.changed_keys or self.only_in_left or self.only_in_right)

    def to_dict(self) -> Dict:
        return {
            "path": self.path,
            "changed_keys": self.changed_keys,
            "only_in_left": self.only_in_left,
            "only_in_right": self.only_in_right,
            "frozen_at": self.frozen_at,
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "FrozenEntry":
        return cls(
            path=data["path"],
            changed_keys=data["changed_keys"],
            only_in_left=data["only_in_left"],
            only_in_right=data["only_in_right"],
            frozen_at=data.get("frozen_at", 0.0),
        )


@dataclass
class FreezeReport:
    entries: List[FrozenEntry] = field(default_factory=list)
    label: str = ""

    def dirty_entries(self) -> List[FrozenEntry]:
        return [e for e in self.entries if e.has_differences()]

    def to_dict(self) -> Dict:
        return {
            "label": self.label,
            "entries": [e.to_dict() for e in self.entries],
        }


def freeze_diffs(diffs: List[SecretDiff], label: str = "") -> FreezeReport:
    entries = [
        FrozenEntry(
            path=d.path,
            changed_keys=list(d.changed_keys.keys()),
            only_in_left=list(d.only_in_left.keys()),
            only_in_right=list(d.only_in_right.keys()),
        )
        for d in diffs
    ]
    return FreezeReport(entries=entries, label=label)


def save_freeze(report: FreezeReport, path: str) -> None:
    Path(path).write_text(json.dumps(report.to_dict(), indent=2))


def load_freeze(path: str) -> Optional[FreezeReport]:
    p = Path(path)
    if not p.exists():
        return None
    data = json.loads(p.read_text())
    entries = [FrozenEntry.from_dict(e) for e in data.get("entries", [])]
    return FreezeReport(entries=entries, label=data.get("label", ""))
