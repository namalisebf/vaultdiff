"""Classify secret paths by sensitivity tier based on key patterns."""
from __future__ import annotations

from dataclasses import dataclass, field
from fnmatch import fnmatch
from typing import Dict, List, Optional

from vaultdiff.differ import SecretDiff


SENSITIVITY_TIERS = ("critical", "high", "medium", "low")

_DEFAULT_RULES: Dict[str, List[str]] = {
    "critical": ["*password*", "*secret*", "*private_key*", "*master_key*"],
    "high": ["*token*", "*api_key*", "*credential*", "*auth*"],
    "medium": ["*cert*", "*ssl*", "*tls*", "*dsn*"],
    "low": ["*"],
}


@dataclass
class ClassifiedPath:
    path: str
    tier: str
    matched_keys: List[str] = field(default_factory=list)
    diff: Optional[SecretDiff] = field(default=None, repr=False)

    def to_dict(self) -> dict:
        return {
            "path": self.path,
            "tier": self.tier,
            "matched_keys": self.matched_keys,
        }


@dataclass
class ClassifierConfig:
    rules: Dict[str, List[str]] = field(default_factory=lambda: dict(_DEFAULT_RULES))

    @classmethod
    def from_dict(cls, data: dict) -> "ClassifierConfig":
        rules = {tier: list(patterns) for tier, patterns in data.get("rules", {}).items()}
        return cls(rules=rules or dict(_DEFAULT_RULES))


def _tier_for_key(key: str, rules: Dict[str, List[str]]) -> str:
    for tier in SENSITIVITY_TIERS:
        for pattern in rules.get(tier, []):
            if fnmatch(key.lower(), pattern.lower()):
                return tier
    return "low"


def classify_diffs(
    diffs: List[SecretDiff],
    config: Optional[ClassifierConfig] = None,
) -> List[ClassifiedPath]:
    """Assign a sensitivity tier to each diff based on its key names."""
    cfg = config or ClassifierConfig()
    results: List[ClassifiedPath] = []

    for diff in diffs:
        all_keys = (
            list(diff.changed_keys.keys())
            + list(diff.only_in_left.keys())
            + list(diff.only_in_right.keys())
        )
        top_tier = "low"
        matched: List[str] = []
        for key in all_keys:
            tier = _tier_for_key(key, cfg.rules)
            if SENSITIVITY_TIERS.index(tier) < SENSITIVITY_TIERS.index(top_tier):
                top_tier = tier
            matched.append(key)

        results.append(
            ClassifiedPath(path=diff.path, tier=top_tier, matched_keys=matched, diff=diff)
        )

    results.sort(key=lambda r: SENSITIVITY_TIERS.index(r.tier))
    return results
