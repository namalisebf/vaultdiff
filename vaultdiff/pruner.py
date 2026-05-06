"""Pruner: remove stale or redundant secret paths from diff results."""
from __future__ import annotations

from dataclasses import dataclass, field
from fnmatch import fnmatch
from typing import List, Optional

from vaultdiff.differ import SecretDiff


@dataclass
class PruneConfig:
    """Configuration for pruning diff results."""
    # Remove paths whose keys are all unchanged
    drop_clean: bool = False
    # Remove paths matching any of these glob patterns
    exclude_patterns: List[str] = field(default_factory=list)
    # Keep at most this many paths (None = unlimited)
    max_paths: Optional[int] = None

    @classmethod
    def from_dict(cls, data: dict) -> "PruneConfig":
        return cls(
            drop_clean=bool(data.get("drop_clean", False)),
            exclude_patterns=list(data.get("exclude_patterns", [])),
            max_paths=data.get("max_paths"),
        )


@dataclass
class PruneReport:
    kept: List[SecretDiff]
    dropped: List[SecretDiff]

    @property
    def total_dropped(self) -> int:
        return len(self.dropped)

    def to_dict(self) -> dict:
        return {
            "kept": [d.path for d in self.kept],
            "dropped": [d.path for d in self.dropped],
            "total_dropped": self.total_dropped,
        }


def _is_excluded(path: str, patterns: List[str]) -> bool:
    return any(fnmatch(path, p) for p in patterns)


def prune_diffs(diffs: List[SecretDiff], config: PruneConfig) -> PruneReport:
    """Apply pruning rules and return a PruneReport."""
    kept: List[SecretDiff] = []
    dropped: List[SecretDiff] = []

    for diff in diffs:
        if config.drop_clean and not diff.has_differences:
            dropped.append(diff)
            continue
        if _is_excluded(diff.path, config.exclude_patterns):
            dropped.append(diff)
            continue
        kept.append(diff)

    if config.max_paths is not None:
        overflow = kept[config.max_paths:]
        kept = kept[: config.max_paths]
        dropped.extend(overflow)

    return PruneReport(kept=kept, dropped=dropped)
