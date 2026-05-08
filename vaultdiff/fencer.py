"""Fencer: enforce path-level access boundaries for diff operations."""

from __future__ import annotations

from dataclasses import dataclass, field
from fnmatch import fnmatch
from typing import List, Optional


@dataclass
class FenceRule:
    prefix: Optional[str] = None
    glob: Optional[str] = None
    allow: bool = True

    def matches(self, path: str) -> bool:
        if self.prefix and path.startswith(self.prefix):
            return True
        if self.glob and fnmatch(path, self.glob):
            return True
        return False


@dataclass
class FenceConfig:
    rules: List[FenceRule] = field(default_factory=list)
    default_allow: bool = True

    @classmethod
    def from_dict(cls, data: dict) -> "FenceConfig":
        rules = [
            FenceRule(
                prefix=r.get("prefix"),
                glob=r.get("glob"),
                allow=r.get("allow", True),
            )
            for r in data.get("rules", [])
        ]
        return cls(rules=rules, default_allow=data.get("default_allow", True))


@dataclass
class FenceResult:
    path: str
    allowed: bool
    reason: str

    def to_dict(self) -> dict:
        return {"path": self.path, "allowed": self.allowed, "reason": self.reason}


class Fencer:
    def __init__(self, config: FenceConfig) -> None:
        self._config = config

    def check(self, path: str) -> FenceResult:
        for rule in self._config.rules:
            if rule.matches(path):
                reason = "matched rule (allow)" if rule.allow else "matched rule (deny)"
                return FenceResult(path=path, allowed=rule.allow, reason=reason)
        allowed = self._config.default_allow
        reason = "default allow" if allowed else "default deny"
        return FenceResult(path=path, allowed=allowed, reason=reason)

    def filter_paths(self, paths: List[str]) -> List[str]:
        return [p for p in paths if self.check(p).allowed]
