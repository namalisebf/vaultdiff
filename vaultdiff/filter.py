"""Filtering utilities for vault secret paths and keys."""
from __future__ import annotations

import fnmatch
import re
from dataclasses import dataclass, field
from typing import Iterable, List, Optional


@dataclass
class FilterConfig:
    """Configuration for filtering secret paths and keys."""

    include_paths: List[str] = field(default_factory=list)
    exclude_paths: List[str] = field(default_factory=list)
    include_keys: List[str] = field(default_factory=list)
    exclude_keys: List[str] = field(default_factory=list)
    regex: bool = False

    def _match(self, pattern: str, value: str) -> bool:
        if self.regex:
            return bool(re.search(pattern, value))
        return fnmatch.fnmatch(value, pattern)

    def path_allowed(self, path: str) -> bool:
        """Return True if *path* passes include/exclude rules."""
        if self.include_paths:
            if not any(self._match(p, path) for p in self.include_paths):
                return False
        if self.exclude_paths:
            if any(self._match(p, path) for p in self.exclude_paths):
                return False
        return True

    def key_allowed(self, key: str) -> bool:
        """Return True if *key* passes include/exclude rules."""
        if self.include_keys:
            if not any(self._match(k, key) for k in self.include_keys):
                return False
        if self.exclude_keys:
            if any(self._match(k, key) for k in self.exclude_keys):
                return False
        return True

    def filter_paths(self, paths: Iterable[str]) -> List[str]:
        """Return only paths that are allowed."""
        return [p for p in paths if self.path_allowed(p)]

    def filter_keys(self, keys: Iterable[str]) -> List[str]:
        """Return only keys that are allowed."""
        return [k for k in keys if self.key_allowed(k)]


DEFAULT_FILTER = FilterConfig()
