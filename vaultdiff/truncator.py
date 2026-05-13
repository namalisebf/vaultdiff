"""Truncator: limit the number of changed keys reported per diff path."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

from vaultdiff.differ import SecretDiff


@dataclass
class TruncateConfig:
    max_changed_keys: Optional[int] = None
    max_only_in_left: Optional[int] = None
    max_only_in_right: Optional[int] = None

    @classmethod
    def from_dict(cls, data: dict) -> "TruncateConfig":
        return cls(
            max_changed_keys=data.get("max_changed_keys"),
            max_only_in_left=data.get("max_only_in_left"),
            max_only_in_right=data.get("max_only_in_right"),
        )


@dataclass
class TruncatedDiff:
    path: str
    changed_keys: list
    only_in_left: list
    only_in_right: list
    truncated_changed: int = 0
    truncated_left: int = 0
    truncated_right: int = 0

    def has_differences(self) -> bool:
        return bool(self.changed_keys or self.only_in_left or self.only_in_right)

    def to_dict(self) -> dict:
        return {
            "path": self.path,
            "changed_keys": self.changed_keys,
            "only_in_left": self.only_in_left,
            "only_in_right": self.only_in_right,
            "truncated_changed": self.truncated_changed,
            "truncated_left": self.truncated_left,
            "truncated_right": self.truncated_right,
        }


@dataclass
class TruncateReport:
    entries: List[TruncatedDiff] = field(default_factory=list)

    def total_truncated(self) -> int:
        return sum(
            e.truncated_changed + e.truncated_left + e.truncated_right
            for e in self.entries
        )

    def to_dict(self) -> dict:
        return {
            "entries": [e.to_dict() for e in self.entries],
            "total_truncated": self.total_truncated(),
        }


def _limit(items: list, cap: Optional[int]):
    if cap is None or cap < 0:
        return items, 0
    dropped = max(0, len(items) - cap)
    return items[:cap], dropped


def truncate_diffs(diffs: List[SecretDiff], config: TruncateConfig) -> TruncateReport:
    entries: List[TruncatedDiff] = []
    for diff in diffs:
        changed, tc = _limit(diff.changed_keys, config.max_changed_keys)
        left, tl = _limit(diff.only_in_left, config.max_only_in_left)
        right, tr = _limit(diff.only_in_right, config.max_only_in_right)
        entries.append(
            TruncatedDiff(
                path=diff.path,
                changed_keys=changed,
                only_in_left=left,
                only_in_right=right,
                truncated_changed=tc,
                truncated_left=tl,
                truncated_right=tr,
            )
        )
    return TruncateReport(entries=entries)
