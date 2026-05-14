"""Blender: merge multiple SecretDiff lists into a unified view per path."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from vaultdiff.differ import SecretDiff


@dataclass
class BlendedPath:
    path: str
    envs: List[str]
    changed_keys: Dict[str, List[str]]   # key -> list of envs where it changed
    only_in_left: Dict[str, List[str]]   # key -> envs
    only_in_right: Dict[str, List[str]]  # key -> envs

    def has_differences(self) -> bool:
        return bool(self.changed_keys or self.only_in_left or self.only_in_right)

    def to_dict(self) -> dict:
        return {
            "path": self.path,
            "envs": self.envs,
            "has_differences": self.has_differences(),
            "changed_keys": self.changed_keys,
            "only_in_left": self.only_in_left,
            "only_in_right": self.only_in_right,
        }


@dataclass
class BlendReport:
    entries: List[BlendedPath] = field(default_factory=list)

    @property
    def total_paths(self) -> int:
        return len(self.entries)

    @property
    def dirty_paths(self) -> int:
        return sum(1 for e in self.entries if e.has_differences())

    def to_dict(self) -> dict:
        return {
            "total_paths": self.total_paths,
            "dirty_paths": self.dirty_paths,
            "entries": [e.to_dict() for e in self.entries],
        }


def blend_diffs(labeled_diffs: Dict[str, List[SecretDiff]]) -> BlendReport:
    """Merge diffs from multiple environments keyed by env label.

    Args:
        labeled_diffs: mapping of env label -> list of SecretDiff objects.

    Returns:
        BlendReport with one BlendedPath per unique path across all envs.
    """
    path_map: Dict[str, BlendedPath] = {}

    for env, diffs in labeled_diffs.items():
        for diff in diffs:
            if diff.path not in path_map:
                path_map[diff.path] = BlendedPath(
                    path=diff.path,
                    envs=[],
                    changed_keys={},
                    only_in_left={},
                    only_in_right={},
                )
            entry = path_map[diff.path]
            if env not in entry.envs:
                entry.envs.append(env)

            for key in diff.changed_keys:
                entry.changed_keys.setdefault(key, []).append(env)
            for key in diff.only_in_left:
                entry.only_in_left.setdefault(key, []).append(env)
            for key in diff.only_in_right:
                entry.only_in_right.setdefault(key, []).append(env)

    return BlendReport(entries=list(path_map.values()))
