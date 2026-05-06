"""Normalize secret values for consistent comparison across environments."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class NormalizerConfig:
    """Configuration for value normalization rules."""
    strip_whitespace: bool = True
    lowercase_keys: bool = False
    redact_patterns: List[str] = field(default_factory=list)
    replace_rules: Dict[str, str] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "NormalizerConfig":
        return cls(
            strip_whitespace=data.get("strip_whitespace", True),
            lowercase_keys=data.get("lowercase_keys", False),
            redact_patterns=data.get("redact_patterns", []),
            replace_rules=data.get("replace_rules", {}),
        )


@dataclass
class NormalizedSecret:
    path: str
    original: Dict[str, Any]
    normalized: Dict[str, Any]

    def changed_keys(self) -> List[str]:
        """Return keys whose values changed during normalization."""
        return [
            k for k in self.original
            if str(self.original[k]) != str(self.normalized.get(k, ""))
        ]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "path": self.path,
            "original": self.original,
            "normalized": self.normalized,
            "changed_keys": self.changed_keys(),
        }


class Normalizer:
    def __init__(self, config: Optional[NormalizerConfig] = None) -> None:
        self._config = config or NormalizerConfig()
        self._redact_re = [
            re.compile(p, re.IGNORECASE)
            for p in self._config.redact_patterns
        ]

    def normalize_value(self, key: str, value: Any) -> Any:
        if not isinstance(value, str):
            return value
        result = value
        if self._config.strip_whitespace:
            result = result.strip()
        for pattern, replacement in self._config.replace_rules.items():
            result = re.sub(pattern, replacement, result)
        for rx in self._redact_re:
            if rx.search(key):
                result = "***REDACTED***"
                break
        return result

    def normalize_secret(self, path: str, data: Dict[str, Any]) -> NormalizedSecret:
        normalized: Dict[str, Any] = {}
        for k, v in data.items():
            norm_key = k.lower() if self._config.lowercase_keys else k
            normalized[norm_key] = self.normalize_value(k, v)
        return NormalizedSecret(path=path, original=data, normalized=normalized)

    def normalize_many(
        self, secrets: Dict[str, Dict[str, Any]]
    ) -> List[NormalizedSecret]:
        return [self.normalize_secret(path, data) for path, data in secrets.items()]
