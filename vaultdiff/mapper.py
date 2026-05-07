"""Path mapper: rewrite or alias secret paths before comparison."""
from __future__ import annotations

import fnmatch
import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class MapRule:
    pattern: str
    replacement: str
    mode: str = "glob"  # glob | regex | prefix

    def apply(self, path: str) -> Optional[str]:
        """Return rewritten path, or None if rule does not match."""
        if self.mode == "prefix":
            if path.startswith(self.pattern):
                return self.replacement + path[len(self.pattern):]
            return None
        if self.mode == "regex":
            m = re.fullmatch(self.pattern, path)
            if m:
                return m.expand(self.replacement)
            return None
        # glob
        if fnmatch.fnmatch(path, self.pattern):
            # simple glob: replace entire path with replacement
            return self.replacement
        return None


@dataclass
class MapperConfig:
    rules: List[MapRule] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: Dict) -> "MapperConfig":
        rules = [
            MapRule(
                pattern=r["pattern"],
                replacement=r["replacement"],
                mode=r.get("mode", "glob"),
            )
            for r in data.get("rules", [])
        ]
        return cls(rules=rules)


@dataclass
class MappedPath:
    original: str
    mapped: str
    rule_applied: bool

    def to_dict(self) -> Dict:
        return {
            "original": self.original,
            "mapped": self.mapped,
            "rule_applied": self.rule_applied,
        }


class Mapper:
    def __init__(self, config: MapperConfig) -> None:
        self._config = config

    def map_path(self, path: str) -> MappedPath:
        """Apply the first matching rule to *path*."""
        for rule in self._config.rules:
            result = rule.apply(path)
            if result is not None:
                return MappedPath(original=path, mapped=result, rule_applied=True)
        return MappedPath(original=path, mapped=path, rule_applied=False)

    def map_paths(self, paths: List[str]) -> List[MappedPath]:
        return [self.map_path(p) for p in paths]
