"""Stencil: apply a template mask to secret diffs, hiding or renaming keys for display."""
from __future__ import annotations

from dataclasses import dataclass, field
from fnmatch import fnmatch
from typing import Dict, List, Optional

from vaultdiff.differ import SecretDiff


@dataclass
class StencilRule:
    key_pattern: str
    alias: Optional[str] = None   # if set, rename the key in output
    hidden: bool = False           # if True, drop the key entirely

    def matches(self, key: str) -> bool:
        return fnmatch(key, self.key_pattern)


@dataclass
class StencilConfig:
    rules: List[StencilRule] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict) -> "StencilConfig":
        rules = [
            StencilRule(
                key_pattern=r["key_pattern"],
                alias=r.get("alias"),
                hidden=bool(r.get("hidden", False)),
            )
            for r in data.get("rules", [])
        ]
        return cls(rules=rules)


@dataclass
class StencilledPath:
    path: str
    changed_keys: Dict[str, dict]
    only_in_left: Dict[str, str]
    only_in_right: Dict[str, str]

    def has_differences(self) -> bool:
        return bool(self.changed_keys or self.only_in_left or self.only_in_right)

    def to_dict(self) -> dict:
        return {
            "path": self.path,
            "changed_keys": self.changed_keys,
            "only_in_left": self.only_in_left,
            "only_in_right": self.only_in_right,
        }


def _apply_rule(config: StencilConfig, key: str) -> tuple[bool, str]:
    """Return (hidden, display_name) for a key."""
    for rule in config.rules:
        if rule.matches(key):
            if rule.hidden:
                return True, key
            return False, rule.alias if rule.alias else key
    return False, key


def apply_stencil(diff: SecretDiff, config: StencilConfig) -> StencilledPath:
    changed: Dict[str, dict] = {}
    for key, entry in diff.changed_keys.items():
        hidden, display = _apply_rule(config, key)
        if not hidden:
            changed[display] = {"left": entry.left_value, "right": entry.right_value}

    only_left: Dict[str, str] = {}
    for key, val in diff.only_in_left.items():
        hidden, display = _apply_rule(config, key)
        if not hidden:
            only_left[display] = val

    only_right: Dict[str, str] = {}
    for key, val in diff.only_in_right.items():
        hidden, display = _apply_rule(config, key)
        if not hidden:
            only_right[display] = val

    return StencilledPath(
        path=diff.path,
        changed_keys=changed,
        only_in_left=only_left,
        only_in_right=only_right,
    )
