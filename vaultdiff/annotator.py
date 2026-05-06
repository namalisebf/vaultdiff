"""Annotator: attach human-readable notes to secret diff paths based on configurable rules."""

from __future__ import annotations

import fnmatch
import re
from dataclasses import dataclass, field
from typing import List, Optional

from vaultdiff.differ import SecretDiff


@dataclass
class AnnotationRule:
    pattern: str
    note: str
    mode: str = "glob"  # "glob" or "regex"

    def matches(self, path: str) -> bool:
        if self.mode == "regex":
            return bool(re.search(self.pattern, path))
        return fnmatch.fnmatch(path, self.pattern)


@dataclass
class AnnotationConfig:
    rules: List[AnnotationRule] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict) -> "AnnotationConfig":
        rules = [
            AnnotationRule(
                pattern=r["pattern"],
                note=r["note"],
                mode=r.get("mode", "glob"),
            )
            for r in data.get("rules", [])
        ]
        return cls(rules=rules)


@dataclass
class AnnotatedPath:
    path: str
    diff: SecretDiff
    notes: List[str] = field(default_factory=list)

    def has_notes(self) -> bool:
        return len(self.notes) > 0

    def to_dict(self) -> dict:
        return {
            "path": self.path,
            "notes": self.notes,
            "has_differences": self.diff.has_differences(),
        }


def annotate_diffs(
    diffs: List[tuple],  # list of (path, SecretDiff)
    config: AnnotationConfig,
) -> List[AnnotatedPath]:
    """Apply annotation rules to a list of (path, SecretDiff) pairs."""
    results: List[AnnotatedPath] = []
    for path, diff in diffs:
        notes = [rule.note for rule in config.rules if rule.matches(path)]
        results.append(AnnotatedPath(path=path, diff=diff, notes=notes))
    return results
