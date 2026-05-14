"""Collector: gather and aggregate raw secret diffs into a CollectionReport."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

from vaultdiff.differ import SecretDiff


@dataclass
class CollectedEntry:
    path: str
    changed_keys: int
    only_in_left: int
    only_in_right: int
    total_keys: int

    def has_differences(self) -> bool:
        return self.changed_keys > 0 or self.only_in_left > 0 or self.only_in_right > 0

    def to_dict(self) -> dict:
        return {
            "path": self.path,
            "changed_keys": self.changed_keys,
            "only_in_left": self.only_in_left,
            "only_in_right": self.only_in_right,
            "total_keys": self.total_keys,
            "has_differences": self.has_differences(),
        }


@dataclass
class CollectionReport:
    entries: List[CollectedEntry] = field(default_factory=list)

    @property
    def total_paths(self) -> int:
        return len(self.entries)

    @property
    def dirty_paths(self) -> int:
        return sum(1 for e in self.entries if e.has_differences())

    @property
    def clean_paths(self) -> int:
        return self.total_paths - self.dirty_paths

    def to_dict(self) -> dict:
        return {
            "total_paths": self.total_paths,
            "dirty_paths": self.dirty_paths,
            "clean_paths": self.clean_paths,
            "entries": [e.to_dict() for e in self.entries],
        }


def collect_diffs(diffs: List[SecretDiff]) -> CollectionReport:
    entries = []
    for d in diffs:
        changed = len(d.changed_keys)
        left = len(d.only_in_left)
        right = len(d.only_in_right)
        total = changed + left + right
        entries.append(CollectedEntry(
            path=d.path,
            changed_keys=changed,
            only_in_left=left,
            only_in_right=right,
            total_keys=total,
        ))
    return CollectionReport(entries=entries)
