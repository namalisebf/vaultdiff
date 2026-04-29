"""Tag secret paths with user-defined labels for grouping and reporting."""
from __future__ import annotations

import fnmatch
import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class TagRule:
    """A single rule that maps a path pattern to one or more tags."""

    pattern: str
    tags: List[str]
    regex: bool = False

    def matches(self, path: str) -> bool:
        if self.regex:
            return bool(re.search(self.pattern, path))
        return fnmatch.fnmatch(path, self.pattern)


@dataclass
class TaggerConfig:
    """Collection of tag rules."""

    rules: List[TagRule] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict) -> "TaggerConfig":
        rules = [
            TagRule(
                pattern=r["pattern"],
                tags=r["tags"],
                regex=r.get("regex", False),
            )
            for r in data.get("rules", [])
        ]
        return cls(rules=rules)


class Tagger:
    """Assigns tags to secret paths based on configured rules."""

    def __init__(self, config: TaggerConfig) -> None:
        self._config = config

    def tags_for(self, path: str) -> List[str]:
        """Return all tags that apply to *path* (in rule order, deduplicated)."""
        seen: Dict[str, None] = {}
        for rule in self._config.rules:
            if rule.matches(path):
                for tag in rule.tags:
                    seen[tag] = None
        return list(seen.keys())

    def tag_paths(self, paths: List[str]) -> Dict[str, List[str]]:
        """Return a mapping of path -> tags for every path in *paths*."""
        return {p: self.tags_for(p) for p in paths}

    def paths_for_tag(self, tag: str, paths: List[str]) -> List[str]:
        """Return every path in *paths* that carries *tag*."""
        return [p for p in paths if tag in self.tags_for(p)]
