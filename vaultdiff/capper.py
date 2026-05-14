"""Cap the number of reported differences per path to a configurable maximum."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

from vaultdiff.differ import SecretDiff


@dataclass
class CapConfig:
    max_changed_keys: Optional[int] = None
    max_only_in_left: Optional[int] = None
    max_only_in_right: Optional[int] = None

    @classmethod
    def from_dict(cls, data: dict) -> "CapConfig":
        return cls(
            max_changed_keys=data.get("max_changed_keys"),
            max_only_in_left=data.get("max_only_in_left"),
            max_only_in_right=data.get("max_only_in_right"),
        )


@dataclass
class CappedDiff:
    path: str
    changed_keys: List[str]
    only_in_left: List[str]
    only_in_right: List[str]
    dropped_changed: int = 0
    dropped_left: int = 0
    dropped_right: int = 0

    def has_differences(self) -> bool:
        return bool(self.changed_keys or self.only_in_left or self.only_in_right)

    def to_dict(self) -> dict:
        return {
            "path": self.path,
            "changed_keys": self.changed_keys,
            "only_in_left": self.only_in_left,
            "only_in_right": self.only_in_right,
            "dropped_changed": self.dropped_changed,
            "dropped_left": self.dropped_left,
            "dropped_right": self.dropped_right,
        }


@dataclass
class CapReport:
    entries: List[CappedDiff] = field(default_factory=list)

    @property
    def total_paths(self) -> int:
        return len(self.entries)

    @property
    def total_dropped(self) -> int:
        return sum(e.dropped_changed + e.dropped_left + e.dropped_right for e in self.entries)

    def to_dict(self) -> dict:
        return {
            "total_paths": self.total_paths,
            "total_dropped": self.total_dropped,
            "entries": [e.to_dict() for e in self.entries],
        }


def _cap(items: List[str], limit: Optional[int]):
    if limit is None or limit < 0:
        return list(items), 0
    capped = items[:limit]
    dropped = max(0, len(items) - limit)
    return capped, dropped


def cap_diffs(diffs: List[SecretDiff], config: CapConfig) -> CapReport:
    entries = []
    for diff in diffs:
        changed = sorted(diff.changed_keys)
        left = sorted(diff.only_in_left)
        right = sorted(diff.only_in_right)

        capped_changed, drop_c = _cap(changed, config.max_changed_keys)
        capped_left, drop_l = _cap(left, config.max_only_in_left)
        capped_right, drop_r = _cap(right, config.max_only_in_right)

        entries.append(CappedDiff(
            path=diff.path,
            changed_keys=capped_changed,
            only_in_left=capped_left,
            only_in_right=capped_right,
            dropped_changed=drop_c,
            dropped_left=drop_l,
            dropped_right=drop_r,
        ))
    return CapReport(entries=entries)
