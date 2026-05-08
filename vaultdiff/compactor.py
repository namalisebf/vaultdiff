"""Compactor: reduce a list of SecretDiffs by merging duplicate paths and
collapsing redundant change entries across multiple diff runs."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List

from vaultdiff.differ import SecretDiff


@dataclass
class CompactedPath:
    path: str
    changed_keys: List[str]
    only_in_left: List[str]
    only_in_right: List[str]
    occurrence_count: int

    @property
    def has_differences(self) -> bool:
        return bool(self.changed_keys or self.only_in_left or self.only_in_right)

    def to_dict(self) -> dict:
        return {
            "path": self.path,
            "changed_keys": sorted(self.changed_keys),
            "only_in_left": sorted(self.only_in_left),
            "only_in_right": sorted(self.only_in_right),
            "occurrence_count": self.occurrence_count,
            "has_differences": self.has_differences,
        }


@dataclass
class CompactReport:
    paths: List[CompactedPath] = field(default_factory=list)

    @property
    def total_paths(self) -> int:
        return len(self.paths)

    @property
    def dirty_paths(self) -> int:
        return sum(1 for p in self.paths if p.has_differences)

    def to_dict(self) -> dict:
        return {
            "total_paths": self.total_paths,
            "dirty_paths": self.dirty_paths,
            "paths": [p.to_dict() for p in self.paths],
        }


def compact_diffs(diffs: List[SecretDiff]) -> CompactReport:
    """Merge multiple SecretDiff entries for the same path into one CompactedPath.

    Changed keys and exclusive keys are unioned across all occurrences.
    """
    accumulator: Dict[str, CompactedPath] = {}

    for diff in diffs:
        path = diff.path
        changed = set(diff.changed_keys.keys())
        left_only = set(diff.only_in_left.keys())
        right_only = set(diff.only_in_right.keys())

        if path not in accumulator:
            accumulator[path] = CompactedPath(
                path=path,
                changed_keys=list(changed),
                only_in_left=list(left_only),
                only_in_right=list(right_only),
                occurrence_count=1,
            )
        else:
            entry = accumulator[path]
            entry.changed_keys = list(set(entry.changed_keys) | changed)
            entry.only_in_left = list(set(entry.only_in_left) | left_only)
            entry.only_in_right = list(set(entry.only_in_right) | right_only)
            entry.occurrence_count += 1

    return CompactReport(paths=list(accumulator.values()))
