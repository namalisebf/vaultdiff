"""Catalog secret paths with metadata for inventory and discovery."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Dict, Optional

from vaultdiff.differ import SecretDiff


@dataclass
class CatalogEntry:
    path: str
    total_keys: int
    has_differences: bool
    changed_keys: int
    only_in_left: int
    only_in_right: int
    tags: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict:
        return {
            "path": self.path,
            "total_keys": self.total_keys,
            "has_differences": self.has_differences,
            "changed_keys": self.changed_keys,
            "only_in_left": self.only_in_left,
            "only_in_right": self.only_in_right,
            "tags": self.tags,
        }


@dataclass
class CatalogReport:
    entries: List[CatalogEntry] = field(default_factory=list)

    @property
    def total_paths(self) -> int:
        return len(self.entries)

    @property
    def dirty_paths(self) -> int:
        return sum(1 for e in self.entries if e.has_differences)

    def to_dict(self) -> Dict:
        return {
            "total_paths": self.total_paths,
            "dirty_paths": self.dirty_paths,
            "entries": [e.to_dict() for e in self.entries],
        }


def catalog_diffs(
    diffs: List[SecretDiff],
    tags: Optional[Dict[str, List[str]]] = None,
) -> CatalogReport:
    """Build a CatalogReport from a list of SecretDiff objects."""
    tag_map = tags or {}
    entries = []
    for diff in diffs:
        all_keys = (
            set(diff.changed_keys)
            | set(diff.only_in_left)
            | set(diff.only_in_right)
        )
        # Count keys present in either side
        left_keys = set(diff.changed_keys) | set(diff.only_in_left)
        right_keys = set(diff.changed_keys) | set(diff.only_in_right)
        total = len(left_keys | right_keys)
        entry = CatalogEntry(
            path=diff.path,
            total_keys=total,
            has_differences=diff.has_differences,
            changed_keys=len(diff.changed_keys),
            only_in_left=len(diff.only_in_left),
            only_in_right=len(diff.only_in_right),
            tags=tag_map.get(diff.path, []),
        )
        entries.append(entry)
    return CatalogReport(entries=entries)
