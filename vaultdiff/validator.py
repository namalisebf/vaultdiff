"""Validates secret diffs against expected schema rules."""
from __future__ import annotations

from dataclasses import dataclass, field
from fnmatch import fnmatch
from typing import List, Dict, Any

from vaultdiff.differ import SecretDiff


@dataclass
class ValidationRule:
    path_glob: str
    required_keys: List[str] = field(default_factory=list)
    forbidden_keys: List[str] = field(default_factory=list)
    key_pattern: str = ""

    def matches(self, path: str) -> bool:
        return fnmatch(path, self.path_glob)


@dataclass
class ValidationViolation:
    path: str
    rule_glob: str
    message: str

    def to_dict(self) -> Dict[str, Any]:
        return {"path": self.path, "rule": self.rule_glob, "message": self.message}


@dataclass
class ValidationConfig:
    rules: List[ValidationRule] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ValidationConfig":
        rules = [
            ValidationRule(
                path_glob=r["path"],
                required_keys=r.get("required_keys", []),
                forbidden_keys=r.get("forbidden_keys", []),
                key_pattern=r.get("key_pattern", ""),
            )
            for r in data.get("rules", [])
        ]
        return cls(rules=rules)


class Validator:
    def __init__(self, config: ValidationConfig) -> None:
        self._config = config

    def validate(self, diff: SecretDiff) -> List[ValidationViolation]:
        violations: List[ValidationViolation] = []
        all_keys = (
            set(diff.changed.keys())
            | set(diff.only_in_left.keys())
            | set(diff.only_in_right.keys())
        )
        for rule in self._config.rules:
            if not rule.matches(diff.path):
                continue
            for key in rule.required_keys:
                if key not in all_keys:
                    violations.append(
                        ValidationViolation(
                            path=diff.path,
                            rule_glob=rule.path_glob,
                            message=f"Required key '{key}' is missing",
                        )
                    )
            for key in rule.forbidden_keys:
                if key in all_keys:
                    violations.append(
                        ValidationViolation(
                            path=diff.path,
                            rule_glob=rule.path_glob,
                            message=f"Forbidden key '{key}' is present",
                        )
                    )
            if rule.key_pattern:
                import re
                pattern = re.compile(rule.key_pattern)
                for key in all_keys:
                    if not pattern.search(key):
                        violations.append(
                            ValidationViolation(
                                path=diff.path,
                                rule_glob=rule.path_glob,
                                message=f"Key '{key}' does not match pattern '{rule.key_pattern}'",
                            )
                        )
        return violations

    def validate_all(self, diffs: List[SecretDiff]) -> List[ValidationViolation]:
        result: List[ValidationViolation] = []
        for diff in diffs:
            result.extend(self.validate(diff))
        return result
