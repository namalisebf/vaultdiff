"""Trimmer: prune diff results to only the most relevant entries based on thresholds."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

from vaultdiff.differ import SecretDiff


@dataclass
class TrimConfig:
    """Configuration for trimming diff results."""
    max_paths: Optional[int] = None
    min_changed_keys: int = 0
    exclude_clean: bool = False
    only_in_left_threshold: Optional[int] = None
    only_in_right_threshold: Optional[int] = None


@dataclass
class TrimmedResult:
    """Result of a trim operation."""
    kept: List[SecretDiff] = field(default_factory=list)
    dropped: List[SecretDiff] = field(default_factory=list)

    @property
    def total(self) -> int:
        return len(self.kept) + len(self.dropped)

    def to_dict(self) -> dict:
        return {
            "kept": len(self.kept),
            "dropped": len(self.dropped),
            "total": self.total,
            "paths": [d.path for d in self.kept],
        }


def _passes_threshold(diff: SecretDiff, config: TrimConfig) -> bool:
    """Return True if the diff meets the minimum criteria to be kept."""
    if config.exclude_clean and not diff.has_differences:
        return False

    changed_count = len(diff.changed)
    if changed_count < config.min_changed_keys:
        return False

    if config.only_in_left_threshold is not None:
        if len(diff.only_in_left) < config.only_in_left_threshold:
            return False

    if config.only_in_right_threshold is not None:
        if len(diff.only_in_right) < config.only_in_right_threshold:
            return False

    return True


def trim_diffs(diffs: List[SecretDiff], config: TrimConfig) -> TrimmedResult:
    """Filter and limit diffs according to the given TrimConfig."""
    result = TrimmedResult()

    for diff in diffs:
        if _passes_threshold(diff, config):
            result.kept.append(diff)
        else:
            result.dropped.append(diff)

    if config.max_paths is not None:
        overflow = result.kept[config.max_paths:]
        result.kept = result.kept[:config.max_paths]
        result.dropped.extend(overflow)

    return result
