"""Summarizer: produce a high-level statistical summary of diff results."""

from dataclasses import dataclass, field
from typing import List, Dict, Any

from vaultdiff.differ import SecretDiff


@dataclass
class SummaryStats:
    total_paths: int = 0
    paths_with_differences: int = 0
    total_changed_keys: int = 0
    total_added_keys: int = 0
    total_removed_keys: int = 0
    paths_only_in_left: List[str] = field(default_factory=list)
    paths_only_in_right: List[str] = field(default_factory=list)

    @property
    def total_differences(self) -> int:
        return self.total_changed_keys + self.total_added_keys + self.total_removed_keys

    @property
    def clean_paths(self) -> int:
        return self.total_paths - self.paths_with_differences

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_paths": self.total_paths,
            "paths_with_differences": self.paths_with_differences,
            "clean_paths": self.clean_paths,
            "total_differences": self.total_differences,
            "total_changed_keys": self.total_changed_keys,
            "total_added_keys": self.total_added_keys,
            "total_removed_keys": self.total_removed_keys,
            "paths_only_in_left": self.paths_only_in_left,
            "paths_only_in_right": self.paths_only_in_right,
        }


def summarize(diffs: List[SecretDiff]) -> SummaryStats:
    """Aggregate a list of SecretDiff objects into a SummaryStats."""
    stats = SummaryStats()

    for diff in diffs:
        stats.total_paths += 1

        if diff.only_in_left and not diff.only_in_right and not diff.changed:
            # Path exists only on the left side
            stats.paths_only_in_left.append(diff.path)
            stats.paths_with_differences += 1
            continue

        if diff.only_in_right and not diff.only_in_left and not diff.changed:
            # Path exists only on the right side
            stats.paths_only_in_right.append(diff.path)
            stats.paths_with_differences += 1
            continue

        changed = len(diff.changed)
        added = len(diff.only_in_right)
        removed = len(diff.only_in_left)

        if changed or added or removed:
            stats.paths_with_differences += 1

        stats.total_changed_keys += changed
        stats.total_added_keys += added
        stats.total_removed_keys += removed

    return stats


def format_summary_text(stats: SummaryStats) -> str:
    """Render a human-readable summary string."""
    lines = [
        f"Paths scanned       : {stats.total_paths}",
        f"Clean paths         : {stats.clean_paths}",
        f"Paths with diffs    : {stats.paths_with_differences}",
        f"Changed keys        : {stats.total_changed_keys}",
        f"Added keys          : {stats.total_added_keys}",
        f"Removed keys        : {stats.total_removed_keys}",
    ]
    if stats.paths_only_in_left:
        lines.append(f"Only in left        : {', '.join(stats.paths_only_in_left)}")
    if stats.paths_only_in_right:
        lines.append(f"Only in right       : {', '.join(stats.paths_only_in_right)}")
    return "\n".join(lines)
