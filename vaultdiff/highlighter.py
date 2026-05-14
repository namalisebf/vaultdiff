"""Highlight changed keys across a list of SecretDiff results."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Set

from vaultdiff.differ import SecretDiff


@dataclass
class HighlightedPath:
    path: str
    changed_keys: Set[str] = field(default_factory=set)
    added_keys: Set[str] = field(default_factory=set)
    removed_keys: Set[str] = field(default_factory=set)

    @property
    def has_highlights(self) -> bool:
        return bool(self.changed_keys or self.added_keys or self.removed_keys)

    def to_dict(self) -> Dict:
        return {
            "path": self.path,
            "changed_keys": sorted(self.changed_keys),
            "added_keys": sorted(self.added_keys),
            "removed_keys": sorted(self.removed_keys),
            "has_highlights": self.has_highlights,
        }


@dataclass
class HighlightReport:
    entries: List[HighlightedPath] = field(default_factory=list)

    @property
    def total_paths(self) -> int:
        return len(self.entries)

    @property
    def highlighted_paths(self) -> int:
        return sum(1 for e in self.entries if e.has_highlights)

    def to_dict(self) -> Dict:
        return {
            "total_paths": self.total_paths,
            "highlighted_paths": self.highlighted_paths,
            "entries": [e.to_dict() for e in self.entries],
        }


def highlight_diffs(diffs: List[SecretDiff]) -> HighlightReport:
    """Build a HighlightReport from a list of SecretDiff objects."""
    entries: List[HighlightedPath] = []
    for diff in diffs:
        changed: Set[str] = {d.key for d in diff.changed_keys}
        added: Set[str] = {k for k in diff.only_in_right}
        removed: Set[str] = {k for k in diff.only_in_left}
        entries.append(
            HighlightedPath(
                path=diff.path,
                changed_keys=changed,
                added_keys=added,
                removed_keys=removed,
            )
        )
    return HighlightReport(entries=entries)
