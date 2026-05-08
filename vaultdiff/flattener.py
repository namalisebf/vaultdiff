"""Flatten nested SecretDiff lists into a single deduplicated path-keyed mapping."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from vaultdiff.differ import SecretDiff


@dataclass
class FlatEntry:
    path: str
    changed_keys: List[str] = field(default_factory=list)
    only_in_left: List[str] = field(default_factory=list)
    only_in_right: List[str] = field(default_factory=list)
    total_differences: int = 0

    def has_differences(self) -> bool:
        return self.total_differences > 0

    def to_dict(self) -> dict:
        return {
            "path": self.path,
            "changed_keys": self.changed_keys,
            "only_in_left": self.only_in_left,
            "only_in_right": self.only_in_right,
            "total_differences": self.total_differences,
            "has_differences": self.has_differences(),
        }


@dataclass
class FlatReport:
    entries: List[FlatEntry] = field(default_factory=list)

    @property
    def total_paths(self) -> int:
        return len(self.entries)

    @property
    def dirty_paths(self) -> int:
        return sum(1 for e in self.entries if e.has_differences())

    def get(self, path: str) -> Optional[FlatEntry]:
        for entry in self.entries:
            if entry.path == path:
                return entry
        return None

    def to_dict(self) -> dict:
        return {
            "total_paths": self.total_paths,
            "dirty_paths": self.dirty_paths,
            "entries": [e.to_dict() for e in self.entries],
        }


def flatten_diffs(diffs: List[SecretDiff]) -> FlatReport:
    """Collapse a list of SecretDiff objects into a FlatReport.

    Duplicate paths are merged: key lists are unioned and total_differences
    is re-computed from the merged sets.
    """
    merged: Dict[str, FlatEntry] = {}

    for diff in diffs:
        path = diff.path
        if path not in merged:
            merged[path] = FlatEntry(path=path)

        entry = merged[path]

        for key in diff.changed_keys:
            if key not in entry.changed_keys:
                entry.changed_keys.append(key)

        for key in diff.only_in_left:
            if key not in entry.only_in_left:
                entry.only_in_left.append(key)

        for key in diff.only_in_right:
            if key not in entry.only_in_right:
                entry.only_in_right.append(key)

        entry.total_differences = (
            len(entry.changed_keys)
            + len(entry.only_in_left)
            + len(entry.only_in_right)
        )

    return FlatReport(entries=list(merged.values()))
