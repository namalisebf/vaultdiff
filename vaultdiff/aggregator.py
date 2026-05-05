"""Aggregates multiple SecretDiff results into a unified cross-environment report."""

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from vaultdiff.differ import SecretDiff


@dataclass
class AggregatedPath:
    path: str
    environments: List[str]
    total_changed: int
    total_only_in_left: int
    total_only_in_right: int
    details: Dict[str, SecretDiff] = field(default_factory=dict)

    def has_differences(self) -> bool:
        return (
            self.total_changed > 0
            or self.total_only_in_left > 0
            or self.total_only_in_right > 0
        )

    def to_dict(self) -> dict:
        return {
            "path": self.path,
            "environments": self.environments,
            "total_changed": self.total_changed,
            "total_only_in_left": self.total_only_in_left,
            "total_only_in_right": self.total_only_in_right,
            "has_differences": self.has_differences(),
        }


@dataclass
class AggregateReport:
    environments: List[str]
    paths: List[AggregatedPath] = field(default_factory=list)

    @property
    def dirty_paths(self) -> List[AggregatedPath]:
        return [p for p in self.paths if p.has_differences()]

    @property
    def clean_paths(self) -> List[AggregatedPath]:
        return [p for p in self.paths if not p.has_differences()]

    def to_dict(self) -> dict:
        return {
            "environments": self.environments,
            "total_paths": len(self.paths),
            "dirty_paths": len(self.dirty_paths),
            "clean_paths": len(self.clean_paths),
            "paths": [p.to_dict() for p in self.paths],
        }


def aggregate_diffs(
    env_diffs: Dict[str, Dict[str, SecretDiff]],
    environments: Optional[List[str]] = None,
) -> AggregateReport:
    """Aggregate diffs from multiple environments keyed by env name.

    Args:
        env_diffs: Mapping of environment label -> {path -> SecretDiff}.
        environments: Optional ordered list of environment names.

    Returns:
        AggregateReport summarising all paths across environments.
    """
    envs = environments or sorted(env_diffs.keys())
    all_paths: Dict[str, AggregatedPath] = {}

    for env, path_diffs in env_diffs.items():
        for path, diff in path_diffs.items():
            if path not in all_paths:
                all_paths[path] = AggregatedPath(
                    path=path,
                    environments=[],
                    total_changed=0,
                    total_only_in_left=0,
                    total_only_in_right=0,
                )
            entry = all_paths[path]
            if env not in entry.environments:
                entry.environments.append(env)
            entry.total_changed += len(diff.changed)
            entry.total_only_in_left += len(diff.only_in_left)
            entry.total_only_in_right += len(diff.only_in_right)
            entry.details[env] = diff

    return AggregateReport(
        environments=envs,
        paths=sorted(all_paths.values(), key=lambda p: p.path),
    )
