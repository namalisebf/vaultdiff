"""Policy checker: validate that secret keys conform to naming and value rules."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List, Optional

from vaultdiff.differ import SecretDiff


@dataclass
class PolicyViolation:
    path: str
    key: str
    rule: str
    message: str

    def to_dict(self) -> dict:
        return {
            "path": self.path,
            "key": self.key,
            "rule": self.rule,
            "message": self.message,
        }


@dataclass
class PolicyConfig:
    """Rules applied to every key seen in a diff."""
    required_key_pattern: Optional[str] = None   # regex keys must match
    forbidden_key_pattern: Optional[str] = None  # regex keys must NOT match
    max_value_length: Optional[int] = None
    disallow_empty_values: bool = False
    extra_rules: List[str] = field(default_factory=list)


class PolicyChecker:
    def __init__(self, config: PolicyConfig) -> None:
        self.config = config
        self._req_re = (
            re.compile(config.required_key_pattern)
            if config.required_key_pattern
            else None
        )
        self._forb_re = (
            re.compile(config.forbidden_key_pattern)
            if config.forbidden_key_pattern
            else None
        )

    def check_diff(self, diff: SecretDiff) -> List[PolicyViolation]:
        violations: List[PolicyViolation] = []
        all_keys = (
            {k for k, _ in diff.changed_keys}
            | set(diff.only_in_left)
            | set(diff.only_in_right)
        )
        for key in all_keys:
            violations.extend(self._check_key(diff.path, key))

        for key, (_, new_val) in diff.changed_keys:
            violations.extend(self._check_value(diff.path, key, new_val))
        for key in diff.only_in_right:
            val = diff.right_data.get(key, "")
            violations.extend(self._check_value(diff.path, key, val))
        return violations

    def _check_key(self, path: str, key: str) -> List[PolicyViolation]:
        violations = []
        if self._req_re and not self._req_re.search(key):
            violations.append(PolicyViolation(
                path=path, key=key, rule="required_key_pattern",
                message=f"Key '{key}' does not match required pattern '{self.config.required_key_pattern}'",
            ))
        if self._forb_re and self._forb_re.search(key):
            violations.append(PolicyViolation(
                path=path, key=key, rule="forbidden_key_pattern",
                message=f"Key '{key}' matches forbidden pattern '{self.config.forbidden_key_pattern}'",
            ))
        return violations

    def _check_value(self, path: str, key: str, value: str) -> List[PolicyViolation]:
        violations = []
        if self.config.disallow_empty_values and value == "":
            violations.append(PolicyViolation(
                path=path, key=key, rule="disallow_empty_values",
                message=f"Key '{key}' has an empty value",
            ))
        if self.config.max_value_length and len(value) > self.config.max_value_length:
            violations.append(PolicyViolation(
                path=path, key=key, rule="max_value_length",
                message=(
                    f"Key '{key}' value length {len(value)} exceeds max "
                    f"{self.config.max_value_length}"
                ),
            ))
        return violations
