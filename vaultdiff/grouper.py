"""Group diff results by path prefix or custom rules for structured reporting."""

from __future__ import annotations

from dataclasses import dataclass, field
from fnmatch import fnmatch
from typing import Dict, List, Optional

from vaultdiff.differ import SecretDiff


@dataclass
class GroupRule:
    name: str
    pattern: str  # glob pattern matched against path

    def matches(self, path: str) -> bool:
        return fnmatch(path, self.pattern)


@dataclass
class GroupConfig:
    rules: List[GroupRule] = field(default_factory=list)
    default_group: str = "other"

    @classmethod
    def from_dict(cls, data: dict) -> "GroupConfig":
        rules = [
            GroupRule(name=r["name"], pattern=r["pattern"])
            for r in data.get("rules", [])
        ]
        return cls(
            rules=rules,
            default_group=data.get("default_group", "other"),
        )


@dataclass
class PathGroup:
    name: str
    paths: List[str] = field(default_factory=list)
    diffs: List[SecretDiff] = field(default_factory=list)

    @property
    def total_differences(self) -> int:
        return sum(
            len(d.changed_keys) + len(d.only_in_left) + len(d.only_in_right)
            for d in self.diffs
        )

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "paths": self.paths,
            "total_differences": self.total_differences,
            "path_count": len(self.paths),
        }


def group_diffs(
    diffs: List[SecretDiff],
    config: Optional[GroupConfig] = None,
) -> Dict[str, PathGroup]:
    """Assign each diff to a named group based on GroupConfig rules."""
    if config is None:
        config = GroupConfig()

    groups: Dict[str, PathGroup] = {}

    for diff in diffs:
        assigned = config.default_group
        for rule in config.rules:
            if rule.matches(diff.path):
                assigned = rule.name
                break
        if assigned not in groups:
            groups[assigned] = PathGroup(name=assigned)
        groups[assigned].paths.append(diff.path)
        groups[assigned].diffs.append(diff)

    return groups
