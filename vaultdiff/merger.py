"""Merge multiple SecretDiff results into a unified view across environments."""
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from vaultdiff.differ import SecretDiff


@dataclass
class MergedKey:
    key: str
    values: Dict[str, Optional[str]]  # env_label -> value (None = missing)

    def is_consistent(self) -> bool:
        """Return True if all present values are identical."""
        present = [v for v in self.values.values() if v is not None]
        return len(set(present)) <= 1

    def to_dict(self) -> dict:
        return {
            "key": self.key,
            "values": self.values,
            "consistent": self.is_consistent(),
        }


@dataclass
class MergedPath:
    path: str
    keys: List[MergedKey] = field(default_factory=list)

    def inconsistent_keys(self) -> List[MergedKey]:
        return [k for k in self.keys if not k.is_consistent()]

    def is_clean(self) -> bool:
        return len(self.inconsistent_keys()) == 0

    def to_dict(self) -> dict:
        return {
            "path": self.path,
            "clean": self.is_clean(),
            "keys": [k.to_dict() for k in self.keys],
        }


def merge_diffs(labeled_diffs: Dict[str, List[SecretDiff]]) -> List[MergedPath]:
    """Merge diffs from multiple environments into MergedPath objects.

    Args:
        labeled_diffs: mapping of env_label -> list of SecretDiff for that env pair.
            Each SecretDiff must have a ``path`` attribute and ``left`` / ``right`` dicts.
    Returns:
        List of MergedPath, one per unique path across all envs.
    """
    # Collect all unique paths
    path_envs: Dict[str, Dict[str, Dict[str, Optional[str]]]] = {}
    # path -> key -> env_label -> value

    for env_label, diffs in labeled_diffs.items():
        for diff in diffs:
            path = diff.path
            if path not in path_envs:
                path_envs[path] = {}
            all_keys = set(diff.left.keys()) | set(diff.right.keys())
            for key in all_keys:
                if key not in path_envs[path]:
                    path_envs[path][key] = {}
                # Prefer right (target env) value; fall back to left
                value = diff.right.get(key, diff.left.get(key))
                path_envs[path][key][env_label] = value

    merged: List[MergedPath] = []
    for path, keys_map in sorted(path_envs.items()):
        merged_keys = [
            MergedKey(key=k, values=env_vals)
            for k, env_vals in sorted(keys_map.items())
        ]
        merged.append(MergedPath(path=path, keys=merged_keys))
    return merged
