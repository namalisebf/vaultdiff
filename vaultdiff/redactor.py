"""Redaction utilities for masking sensitive secret values in output."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List, Optional

DEFAULT_MASK = "***REDACTED***"

DEFAULT_SENSITIVE_PATTERNS: List[str] = [
    r"(?i)password",
    r"(?i)secret",
    r"(?i)token",
    r"(?i)api[_-]?key",
    r"(?i)private[_-]?key",
    r"(?i)credentials?",
]


@dataclass
class RedactorConfig:
    """Configuration for the secret value redactor."""

    enabled: bool = True
    mask: str = DEFAULT_MASK
    key_patterns: List[str] = field(default_factory=lambda: list(DEFAULT_SENSITIVE_PATTERNS))
    additional_patterns: List[str] = field(default_factory=list)

    def all_patterns(self) -> List[str]:
        return self.key_patterns + self.additional_patterns


class Redactor:
    """Redacts sensitive values based on key name patterns."""

    def __init__(self, config: Optional[RedactorConfig] = None) -> None:
        self.config = config or RedactorConfig()
        self._compiled = [
            re.compile(p) for p in self.config.all_patterns()
        ]

    def is_sensitive(self, key: str) -> bool:
        """Return True if the key name matches any sensitive pattern."""
        if not self.config.enabled:
            return False
        return any(rx.search(key) for rx in self._compiled)

    def redact_value(self, key: str, value: str) -> str:
        """Return the masked value if the key is sensitive, otherwise the original."""
        if self.is_sensitive(key):
            return self.config.mask
        return value

    def redact_dict(self, data: dict) -> dict:
        """Return a copy of *data* with sensitive values replaced by the mask."""
        return {k: self.redact_value(k, v) for k, v in data.items()}
