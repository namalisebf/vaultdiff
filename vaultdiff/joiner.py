"""Join multiple SecretDiff lists by path, producing a unified view."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from vaultdiff.differ import SecretDiff


@dataclass
class JoinedPath:
    path: str
    entries: Dict[str, SecretDiff] = field(default_factory=dict)

    def labels(self) -> List[str]:
        return list(self.entries.keys())

    def has_differences(self) -> bool:
        return any(d.has_differences() for d in self.entries.values())

    def to_dict(self) -> dict:
        return {
            "path": self.path,
            "has_differences": self.has_differences(),
            "entries": {
                label: {
                    "changed": list(diff.changed),
                    "only_in_left": list(diff.only_in_left),
                    "only_in_right": list(diff.only_in_right),
                }
                for label, diff in self.entries.items()
            },
        }


@dataclass
class JoinReport:
    joined: List[JoinedPath] = field(default_factory=list)

    @property
    def total_paths(self) -> int:
        return len(self.joined)

    @property
    def dirty_paths(self) -> int:
        return sum(1 for j in self.joined if j.has_differences())

    def to_dict(self) -> dict:
        return {
            "total_paths": self.total_paths,
            "dirty_paths": self.dirty_paths,
            "joined": [j.to_dict() for j in self.joined],
        }


def join_diffs(labeled_diffs: Dict[str, List[SecretDiff]]) -> JoinReport:
    """Merge multiple labeled diff lists into a single JoinReport keyed by path."""
    path_map: Dict[str, JoinedPath] = {}

    for label, diffs in labeled_diffs.items():
        for diff in diffs:
            if diff.path not in path_map:
                path_map[diff.path] = JoinedPath(path=diff.path)
            path_map[diff.path].entries[label] = diff

    return JoinReport(joined=list(path_map.values()))
