"""Correlate secret diffs across multiple environments to identify patterns."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from vaultdiff.differ import SecretDiff


@dataclass
class CorrelatedKey:
    key: str
    environments_changed: List[str]
    environments_clean: List[str]

    @property
    def change_count(self) -> int:
        return len(self.environments_changed)

    @property
    def is_universal_change(self) -> bool:
        return len(self.environments_clean) == 0 and self.change_count > 0

    def to_dict(self) -> dict:
        return {
            "key": self.key,
            "environments_changed": self.environments_changed,
            "environments_clean": self.environments_clean,
            "change_count": self.change_count,
            "is_universal_change": self.is_universal_change,
        }


@dataclass
class CorrelatedPath:
    path: str
    keys: List[CorrelatedKey] = field(default_factory=list)

    @property
    def universal_change_keys(self) -> List[CorrelatedKey]:
        return [k for k in self.keys if k.is_universal_change]

    @property
    def partial_change_keys(self) -> List[CorrelatedKey]:
        return [k for k in self.keys if 0 < k.change_count and not k.is_universal_change]

    def to_dict(self) -> dict:
        return {
            "path": self.path,
            "keys": [k.to_dict() for k in self.keys],
            "universal_change_count": len(self.universal_change_keys),
            "partial_change_count": len(self.partial_change_keys),
        }


@dataclass
class CorrelationReport:
    paths: List[CorrelatedPath] = field(default_factory=list)

    @property
    def total_paths(self) -> int:
        return len(self.paths)

    @property
    def paths_with_universal_changes(self) -> List[CorrelatedPath]:
        return [p for p in self.paths if p.universal_change_keys]

    def to_dict(self) -> dict:
        return {
            "total_paths": self.total_paths,
            "paths_with_universal_changes": len(self.paths_with_universal_changes),
            "paths": [p.to_dict() for p in self.paths],
        }


def correlate_diffs(env_diffs: Dict[str, List[SecretDiff]]) -> CorrelationReport:
    """Given a mapping of env_name -> list of SecretDiff, correlate key-level changes."""
    path_map: Dict[str, Dict[str, CorrelatedKey]] = {}
    all_envs = list(env_diffs.keys())

    for env, diffs in env_diffs.items():
        for diff in diffs:
            path = diff.path
            if path not in path_map:
                path_map[path] = {}
            changed_keys = set(diff.changed_keys) | set(diff.only_in_left) | set(diff.only_in_right)
            for key in changed_keys:
                if key not in path_map[path]:
                    path_map[path][key] = CorrelatedKey(
                        key=key,
                        environments_changed=[],
                        environments_clean=[],
                    )
                path_map[path][key].environments_changed.append(env)

    for path, key_map in path_map.items():
        for key, ck in key_map.items():
            ck.environments_clean = [e for e in all_envs if e not in ck.environments_changed]

    report_paths = [
        CorrelatedPath(path=path, keys=list(key_map.values()))
        for path, key_map in sorted(path_map.items())
    ]
    return CorrelationReport(paths=report_paths)
