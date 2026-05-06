"""Trace the history of changes across multiple diff snapshots for a path."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from vaultdiff.differ import SecretDiff


@dataclass
class TracePoint:
    """A single point in the change history of a secret path."""

    label: str
    path: str
    changed_keys: List[str] = field(default_factory=list)
    only_in_left: List[str] = field(default_factory=list)
    only_in_right: List[str] = field(default_factory=list)

    @property
    def has_changes(self) -> bool:
        return bool(self.changed_keys or self.only_in_left or self.only_in_right)

    def to_dict(self) -> dict:
        return {
            "label": self.label,
            "path": self.path,
            "has_changes": self.has_changes,
            "changed_keys": self.changed_keys,
            "only_in_left": self.only_in_left,
            "only_in_right": self.only_in_right,
        }


@dataclass
class TraceReport:
    """Full trace report for one or more paths across labelled diff sets."""

    points: List[TracePoint] = field(default_factory=list)

    @property
    def paths_with_changes(self) -> List[str]:
        return sorted({p.path for p in self.points if p.has_changes})

    @property
    def total_changes(self) -> int:
        return sum(
            len(p.changed_keys) + len(p.only_in_left) + len(p.only_in_right)
            for p in self.points
        )

    def to_dict(self) -> dict:
        return {
            "total_changes": self.total_changes,
            "paths_with_changes": self.paths_with_changes,
            "points": [p.to_dict() for p in self.points],
        }


def trace_diffs(label: str, diffs: List[SecretDiff]) -> List[TracePoint]:
    """Convert a list of SecretDiff objects into TracePoints for a given label."""
    points: List[TracePoint] = []
    for diff in diffs:
        points.append(
            TracePoint(
                label=label,
                path=diff.path,
                changed_keys=list(diff.changed_keys.keys()),
                only_in_left=list(diff.only_in_left.keys()),
                only_in_right=list(diff.only_in_right.keys()),
            )
        )
    return points


def build_trace_report(
    labelled_diffs: Dict[str, List[SecretDiff]],
) -> TraceReport:
    """Build a TraceReport from a mapping of label -> list of SecretDiff."""
    all_points: List[TracePoint] = []
    for label, diffs in labelled_diffs.items():
        all_points.extend(trace_diffs(label, diffs))
    return TraceReport(points=all_points)
