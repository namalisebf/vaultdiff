"""Tag diffs with environment-aware labels based on path patterns."""
from __future__ import annotations

from dataclasses import dataclass, field
from fnmatch import fnmatch
from typing import Dict, List, Optional

from vaultdiff.differ import SecretDiff


@dataclass
class EnvTagRule:
    pattern: str
    tag: str
    env: Optional[str] = None  # None means apply to all envs
    mode: str = "glob"  # glob | prefix

    def matches(self, path: str, env: Optional[str] = None) -> bool:
        if self.env is not None and env != self.env:
            return False
        if self.mode == "prefix":
            return path.startswith(self.pattern)
        return fnmatch(path, self.pattern)


@dataclass
class EnvTagConfig:
    rules: List[EnvTagRule] = field(default_factory=list)
    default_tag: str = "untagged"

    @classmethod
    def from_dict(cls, data: dict) -> "EnvTagConfig":
        rules = [
            EnvTagRule(
                pattern=r["pattern"],
                tag=r["tag"],
                env=r.get("env"),
                mode=r.get("mode", "glob"),
            )
            for r in data.get("rules", [])
        ]
        return cls(rules=rules, default_tag=data.get("default_tag", "untagged"))


@dataclass
class EnvTaggedPath:
    path: str
    tag: str
    diff: SecretDiff

    def to_dict(self) -> dict:
        return {
            "path": self.path,
            "tag": self.tag,
            "has_differences": self.diff.has_differences(),
        }


def tag_diffs(
    diffs: List[SecretDiff],
    config: EnvTagConfig,
    env: Optional[str] = None,
) -> List[EnvTaggedPath]:
    results: List[EnvTaggedPath] = []
    for diff in diffs:
        tag = config.default_tag
        for rule in config.rules:
            if rule.matches(diff.path, env=env):
                tag = rule.tag
                break
        results.append(EnvTaggedPath(path=diff.path, tag=tag, diff=diff))
    return results
