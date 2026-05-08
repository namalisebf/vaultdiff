"""Censor module: redacts or blanks secret values in diffs based on configurable rules."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List, Optional

from vaultdiff.differ import SecretDiff

_PLACEHOLDER = "***CENSORED***"


@dataclass
class CensorRule:
    """A single rule that matches a key pattern and optionally a path pattern."""

    key_pattern: str
    path_pattern: Optional[str] = None
    mode: str = "glob"  # 'glob' | 'regex'

    def matches_key(self, key: str) -> bool:
        if self.mode == "regex":
            return bool(re.search(self.key_pattern, key))
        import fnmatch
        return fnmatch.fnmatch(key, self.key_pattern)

    def matches_path(self, path: str) -> bool:
        if self.path_pattern is None:
            return True
        if self.mode == "regex":
            return bool(re.search(self.path_pattern, path))
        import fnmatch
        return fnmatch.fnmatch(path, self.path_pattern)


@dataclass
class CensorConfig:
    rules: List[CensorRule] = field(default_factory=list)
    placeholder: str = _PLACEHOLDER

    @classmethod
    def from_dict(cls, data: dict) -> "CensorConfig":
        rules = [
            CensorRule(
                key_pattern=r["key_pattern"],
                path_pattern=r.get("path_pattern"),
                mode=r.get("mode", "glob"),
            )
            for r in data.get("rules", [])
        ]
        return cls(
            rules=rules,
            placeholder=data.get("placeholder", _PLACEHOLDER),
        )


@dataclass
class CensoredDiff:
    path: str
    changed: dict
    only_in_left: dict
    only_in_right: dict

    def has_differences(self) -> bool:
        return bool(self.changed or self.only_in_left or self.only_in_right)

    def to_dict(self) -> dict:
        return {
            "path": self.path,
            "changed": self.changed,
            "only_in_left": self.only_in_left,
            "only_in_right": self.only_in_right,
        }


def censor_diff(diff: SecretDiff, config: CensorConfig) -> CensoredDiff:
    """Return a new CensoredDiff with sensitive values replaced by the placeholder."""

    def _should_censor(key: str) -> bool:
        return any(
            r.matches_key(key) and r.matches_path(diff.path)
            for r in config.rules
        )

    ph = config.placeholder

    changed = {
        k: {"left": ph if _should_censor(k) else v["left"],
             "right": ph if _should_censor(k) else v["right"]}
        for k, v in diff.changed.items()
    }
    only_in_left = {
        k: ph if _should_censor(k) else v
        for k, v in diff.only_in_left.items()
    }
    only_in_right = {
        k: ph if _should_censor(k) else v
        for k, v in diff.only_in_right.items()
    }
    return CensoredDiff(
        path=diff.path,
        changed=changed,
        only_in_left=only_in_left,
        only_in_right=only_in_right,
    )
