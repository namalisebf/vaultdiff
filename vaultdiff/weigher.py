"""Weigher: assigns numeric weights to secret diff paths based on configurable rules."""
from __future__ import annotations

import fnmatch
import re
from dataclasses import dataclass, field
from typing import List, Optional

from vaultdiff.differ import SecretDiff


@dataclass
class WeightRule:
    pattern: str
    weight: float
    mode: str = "glob"  # "glob" | "prefix" | "regex"

    def matches(self, path: str) -> bool:
        if self.mode == "prefix":
            return path.startswith(self.pattern)
        if self.mode == "regex":
            return bool(re.search(self.pattern, path))
        return fnmatch.fnmatch(path, self.pattern)


@dataclass
class WeightConfig:
    rules: List[WeightRule] = field(default_factory=list)
    default_weight: float = 1.0

    @classmethod
    def from_dict(cls, data: dict) -> "WeightConfig":
        rules = [
            WeightRule(
                pattern=r["pattern"],
                weight=float(r["weight"]),
                mode=r.get("mode", "glob"),
            )
            for r in data.get("rules", [])
        ]
        return cls(
            rules=rules,
            default_weight=float(data.get("default_weight", 1.0)),
        )


@dataclass
class WeighedPath:
    path: str
    weight: float
    matched_rule: Optional[str]

    def to_dict(self) -> dict:
        return {
            "path": self.path,
            "weight": self.weight,
            "matched_rule": self.matched_rule,
        }


def weigh_diffs(diffs: List[SecretDiff], config: WeightConfig) -> List[WeighedPath]:
    """Return a WeighedPath for each diff, sorted descending by weight."""
    results: List[WeighedPath] = []
    for diff in diffs:
        matched_rule: Optional[str] = None
        weight = config.default_weight
        for rule in config.rules:
            if rule.matches(diff.path):
                weight = rule.weight
                matched_rule = rule.pattern
                break
        results.append(WeighedPath(path=diff.path, weight=weight, matched_rule=matched_rule))
    results.sort(key=lambda wp: wp.weight, reverse=True)
    return results
