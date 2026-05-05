"""Label secret paths based on configurable rules for categorization and reporting."""

from __future__ import annotations

import fnmatch
import re
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class LabelRule:
    label: str
    pattern: str
    mode: str = "glob"  # "glob" or "regex"

    def matches(self, path: str) -> bool:
        if self.mode == "regex":
            return bool(re.search(self.pattern, path))
        return fnmatch.fnmatch(path, self.pattern)


@dataclass
class LabelConfig:
    rules: List[LabelRule] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict) -> "LabelConfig":
        rules = [
            LabelRule(
                label=r["label"],
                pattern=r["pattern"],
                mode=r.get("mode", "glob"),
            )
            for r in data.get("rules", [])
        ]
        return cls(rules=rules)


@dataclass
class LabeledPath:
    path: str
    labels: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {"path": self.path, "labels": self.labels}


class Labeler:
    def __init__(self, config: LabelConfig) -> None:
        self._config = config

    def label_path(self, path: str) -> LabeledPath:
        """Return a LabeledPath with all matching labels applied."""
        labels = [
            rule.label
            for rule in self._config.rules
            if rule.matches(path)
        ]
        return LabeledPath(path=path, labels=labels)

    def label_paths(self, paths: List[str]) -> List[LabeledPath]:
        """Label a list of paths."""
        return [self.label_path(p) for p in paths]

    def paths_with_label(self, labeled: List[LabeledPath], label: str) -> List[LabeledPath]:
        """Filter labeled paths to only those carrying a specific label."""
        return [lp for lp in labeled if label in lp.labels]
