"""Zipper: pair up diffs from two independent runs by path for side-by-side comparison."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from vaultdiff.differ import SecretDiff


@dataclass
class ZippedPath:
    path: str
    left_diff: Optional[SecretDiff]
    right_diff: Optional[SecretDiff]

    @property
    def in_both(self) -> bool:
        return self.left_diff is not None and self.right_diff is not None

    @property
    def only_in_left(self) -> bool:
        return self.left_diff is not None and self.right_diff is None

    @property
    def only_in_right(self) -> bool:
        return self.left_diff is None and self.right_diff is not None

    def to_dict(self) -> dict:
        def _diff_summary(d: Optional[SecretDiff]) -> Optional[dict]:
            if d is None:
                return None
            return {
                "has_differences": d.has_differences(),
                "changed_keys": list(d.changed_keys),
                "only_in_left": list(d.only_in_left),
                "only_in_right": list(d.only_in_right),
            }

        return {
            "path": self.path,
            "in_both": self.in_both,
            "only_in_left": self.only_in_left,
            "only_in_right": self.only_in_right,
            "left_diff": _diff_summary(self.left_diff),
            "right_diff": _diff_summary(self.right_diff),
        }


@dataclass
class ZipReport:
    entries: List[ZippedPath] = field(default_factory=list)

    @property
    def total_paths(self) -> int:
        return len(self.entries)

    @property
    def matched_paths(self) -> int:
        return sum(1 for e in self.entries if e.in_both)

    @property
    def unmatched_paths(self) -> int:
        return self.total_paths - self.matched_paths

    def to_dict(self) -> dict:
        return {
            "total_paths": self.total_paths,
            "matched_paths": self.matched_paths,
            "unmatched_paths": self.unmatched_paths,
            "entries": [e.to_dict() for e in self.entries],
        }


def zip_diffs(
    left: List[SecretDiff],
    right: List[SecretDiff],
) -> ZipReport:
    """Pair diffs from two runs by path, producing a ZipReport."""
    left_map: Dict[str, SecretDiff] = {d.path: d for d in left}
    right_map: Dict[str, SecretDiff] = {d.path: d for d in right}
    all_paths = sorted(set(left_map) | set(right_map))
    entries = [
        ZippedPath(
            path=p,
            left_diff=left_map.get(p),
            right_diff=right_map.get(p),
        )
        for p in all_paths
    ]
    return ZipReport(entries=entries)
