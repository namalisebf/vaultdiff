"""Mark secret diff paths with user-defined labels based on configurable rules."""
from __future__ import annotations

import fnmatch
import re
from dataclasses import dataclass, field
from typing import List, Optional

from vaultdiff.differ import SecretDiff


@dataclass
class MarkRule:
    pattern: str
    mark: str
    mode: str = "glob"  # glob | prefix | regex

    def matches(self, path: str) -> bool:
        if self.mode == "prefix":
            return path.startswith(self.pattern)
        if self.mode == "regex":
            return bool(re.search(self.pattern, path))
        return fnmatch.fnmatch(path, self.pattern)


@dataclass
class MarkConfig:
    rules: List[MarkRule] = field(default_factory=list)
    default_mark: str = ""

    @classmethod
    def from_dict(cls, data: dict) -> "MarkConfig":
        rules = [
            MarkRule(
                pattern=r["pattern"],
                mark=r["mark"],
                mode=r.get("mode", "glob"),
            )
            for r in data.get("rules", [])
        ]
        return cls(rules=rules, default_mark=data.get("default_mark", ""))


@dataclass
class MarkedPath:
    path: str
    mark: str
    diff: SecretDiff

    def has_differences(self) -> bool:
        return self.diff.has_differences()

    def to_dict(self) -> dict:
        return {
            "path": self.path,
            "mark": self.mark,
            "has_differences": self.has_differences(),
            "changed_keys": list(self.diff.changed_keys),
            "only_in_left": list(self.diff.only_in_left),
            "only_in_right": list(self.diff.only_in_right),
        }


@dataclass
class MarkReport:
    entries: List[MarkedPath] = field(default_factory=list)

    def total_paths(self) -> int:
        return len(self.entries)

    def dirty_paths(self) -> int:
        return sum(1 for e in self.entries if e.has_differences())

    def to_dict(self) -> dict:
        return {
            "total_paths": self.total_paths(),
            "dirty_paths": self.dirty_paths(),
            "entries": [e.to_dict() for e in self.entries],
        }


def mark_diffs(diffs: List[SecretDiff], config: Optional[MarkConfig] = None) -> MarkReport:
    cfg = config or MarkConfig()
    entries: List[MarkedPath] = []
    for diff in diffs:
        mark = cfg.default_mark
        for rule in cfg.rules:
            if rule.matches(diff.path):
                mark = rule.mark
                break
        entries.append(MarkedPath(path=diff.path, mark=mark, diff=diff))
    return MarkReport(entries=entries)
