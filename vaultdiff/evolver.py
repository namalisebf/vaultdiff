"""Track how a secret path's diff profile changes across multiple snapshots over time."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Dict, Any

from vaultdiff.differ import SecretDiff


@dataclass
class EvolutionPoint:
    label: str
    changed_keys: int
    only_in_left: int
    only_in_right: int
    total_differences: int

    def to_dict(self) -> Dict[str, Any]:
        return {
            "label": self.label,
            "changed_keys": self.changed_keys,
            "only_in_left": self.only_in_left,
            "only_in_right": self.only_in_right,
            "total_differences": self.total_differences,
        }


@dataclass
class EvolutionTrack:
    path: str
    points: List[EvolutionPoint] = field(default_factory=list)

    def is_growing(self) -> bool:
        """Return True if total_differences strictly increases across all points."""
        if len(self.points) < 2:
            return False
        return all(
            self.points[i].total_differences < self.points[i + 1].total_differences
            for i in range(len(self.points) - 1)
        )

    def is_stable(self) -> bool:
        """Return True if total_differences never changes."""
        if not self.points:
            return True
        return len({p.total_differences for p in self.points}) == 1

    def to_dict(self) -> Dict[str, Any]:
        return {
            "path": self.path,
            "points": [p.to_dict() for p in self.points],
            "is_growing": self.is_growing(),
            "is_stable": self.is_stable(),
        }


def build_evolution_point(label: str, diff: SecretDiff) -> EvolutionPoint:
    return EvolutionPoint(
        label=label,
        changed_keys=len(diff.changed_keys),
        only_in_left=len(diff.only_in_left),
        only_in_right=len(diff.only_in_right),
        total_differences=len(diff.changed_keys) + len(diff.only_in_left) + len(diff.only_in_right),
    )


def evolve_diffs(labeled_diffs: List[tuple[str, List[SecretDiff]]]) -> List[EvolutionTrack]:
    """Build evolution tracks from a sequence of (label, diffs) pairs."""
    tracks: Dict[str, EvolutionTrack] = {}
    for label, diffs in labeled_diffs:
        for diff in diffs:
            if diff.path not in tracks:
                tracks[diff.path] = EvolutionTrack(path=diff.path)
            tracks[diff.path].points.append(build_evolution_point(label, diff))
    return list(tracks.values())
