"""Deduplicator: identify and collapse duplicate secret values across paths."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from vaultdiff.differ import SecretDiff


@dataclass
class DuplicateGroup:
    """A group of paths that share an identical value for a given key."""

    key: str
    value: str
    paths: List[str] = field(default_factory=list)

    @property
    def count(self) -> int:
        return len(self.paths)

    def to_dict(self) -> dict:
        return {
            "key": self.key,
            "value_hash": _hash_value(self.value),
            "paths": sorted(self.paths),
            "count": self.count,
        }


@dataclass
class DeduplicationReport:
    """Summary of duplicate values found across a set of diffs."""

    groups: List[DuplicateGroup] = field(default_factory=list)

    @property
    def total_duplicates(self) -> int:
        return sum(g.count for g in self.groups)

    @property
    def unique_keys_with_duplicates(self) -> int:
        return len(self.groups)

    def to_dict(self) -> dict:
        return {
            "total_duplicates": self.total_duplicates,
            "unique_keys_with_duplicates": self.unique_keys_with_duplicates,
            "groups": [g.to_dict() for g in self.groups],
        }


def _hash_value(value: str) -> str:
    """Return a short hash of a secret value for safe display."""
    import hashlib

    return hashlib.sha256(value.encode()).hexdigest()[:12]


def deduplicate(
    diffs: List[SecretDiff],
    side: str = "left",
    min_count: int = 2,
) -> DeduplicationReport:
    """Detect keys whose values are identical across multiple paths.

    Args:
        diffs: List of SecretDiff objects (one per path).
        side: Which side to inspect — ``"left"`` or ``"right"``.
        min_count: Minimum number of paths sharing the same value to be
            included in the report (default: 2).

    Returns:
        A :class:`DeduplicationReport` listing all duplicate groups.
    """
    if side not in ("left", "right"):
        raise ValueError(f"side must be 'left' or 'right', got {side!r}")

    # key -> value -> [paths]
    index: Dict[str, Dict[str, List[str]]] = {}

    for diff in diffs:
        data: Optional[Dict[str, str]] = diff.left if side == "left" else diff.right
        if not data:
            continue
        for key, value in data.items():
            index.setdefault(key, {}).setdefault(value, []).append(diff.path)

    groups: List[DuplicateGroup] = []
    for key, value_map in sorted(index.items()):
        for value, paths in value_map.items():
            if len(paths) >= min_count:
                groups.append(DuplicateGroup(key=key, value=value, paths=paths))

    return DeduplicationReport(groups=groups)
