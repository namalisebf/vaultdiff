"""Stamper: attach timestamp metadata to secret diffs."""
from __future__ import annotations

import datetime
from dataclasses import dataclass, field
from typing import List, Optional

from vaultdiff.differ import SecretDiff


@dataclass
class StampedDiff:
    path: str
    diff: SecretDiff
    stamped_at: datetime.datetime = field(
        default_factory=lambda: datetime.datetime.now(datetime.timezone.utc)
    )
    label: Optional[str] = None

    def has_differences(self) -> bool:
        return self.diff.has_differences()

    def to_dict(self) -> dict:
        return {
            "path": self.path,
            "stamped_at": self.stamped_at.isoformat(),
            "label": self.label,
            "changed_keys": list(self.diff.changed_keys),
            "only_in_left": list(self.diff.only_in_left),
            "only_in_right": list(self.diff.only_in_right),
            "has_differences": self.has_differences(),
        }


@dataclass
class StampReport:
    entries: List[StampedDiff] = field(default_factory=list)

    @property
    def total_paths(self) -> int:
        return len(self.entries)

    @property
    def dirty_paths(self) -> int:
        return sum(1 for e in self.entries if e.has_differences())

    def to_dict(self) -> dict:
        return {
            "total_paths": self.total_paths,
            "dirty_paths": self.dirty_paths,
            "entries": [e.to_dict() for e in self.entries],
        }


def stamp_diffs(
    diffs: List[SecretDiff],
    label: Optional[str] = None,
    at: Optional[datetime.datetime] = None,
) -> StampReport:
    """Wrap each SecretDiff in a StampedDiff with a timestamp."""
    ts = at or datetime.datetime.now(datetime.timezone.utc)
    entries = [
        StampedDiff(path=d.path, diff=d, stamped_at=ts, label=label)
        for d in diffs
    ]
    return StampReport(entries=entries)
