"""Scoper: restrict diff operations to a declared set of allowed Vault path prefixes."""
from __future__ import annotations

from dataclasses import dataclass, field
from fnmatch import fnmatch
from typing import Iterable, List, Optional


@dataclass
class ScopeConfig:
    """Configuration for path scoping rules."""
    allowed_prefixes: List[str] = field(default_factory=list)
    denied_prefixes: List[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict) -> "ScopeConfig":
        return cls(
            allowed_prefixes=data.get("allowed_prefixes", []),
            denied_prefixes=data.get("denied_prefixes", []),
        )


@dataclass
class ScopedPath:
    path: str
    allowed: bool
    reason: str

    def to_dict(self) -> dict:
        return {"path": self.path, "allowed": self.allowed, "reason": self.reason}


class Scoper:
    """Evaluates whether Vault paths fall within a declared scope."""

    def __init__(self, config: Optional[ScopeConfig] = None) -> None:
        self._config = config or ScopeConfig()

    def _matches_any(self, path: str, patterns: Iterable[str]) -> bool:
        return any(path == p or path.startswith(p.rstrip("/") + "/") or fnmatch(path, p)
                   for p in patterns)

    def is_allowed(self, path: str) -> bool:
        cfg = self._config
        if cfg.denied_prefixes and self._matches_any(path, cfg.denied_prefixes):
            return False
        if cfg.allowed_prefixes:
            return self._matches_any(path, cfg.allowed_prefixes)
        return True

    def evaluate(self, path: str) -> ScopedPath:
        cfg = self._config
        if cfg.denied_prefixes and self._matches_any(path, cfg.denied_prefixes):
            return ScopedPath(path=path, allowed=False, reason="denied by prefix rule")
        if cfg.allowed_prefixes and not self._matches_any(path, cfg.allowed_prefixes):
            return ScopedPath(path=path, allowed=False, reason="not in allowed prefixes")
        return ScopedPath(path=path, allowed=True, reason="within scope")

    def filter_paths(self, paths: Iterable[str]) -> List[str]:
        """Return only paths that are within scope."""
        return [p for p in paths if self.is_allowed(p)]
