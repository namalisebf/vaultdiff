"""Secret path profiling: categorize paths by change frequency and volatility."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Dict

from vaultdiff.differ import SecretDiff


@dataclass
class PathProfile:
    path: str
    total_keys: int
    changed_keys: int
    only_in_left: int
    only_in_right: int
    volatility: float  # 0.0 – 1.0
    category: str  # stable | moderate | volatile

    def to_dict(self) -> Dict:
        return {
            "path": self.path,
            "total_keys": self.total_keys,
            "changed_keys": self.changed_keys,
            "only_in_left": self.only_in_left,
            "only_in_right": self.only_in_right,
            "volatility": round(self.volatility, 4),
            "category": self.category,
        }


def _category(volatility: float) -> str:
    if volatility == 0.0:
        return "stable"
    if volatility < 0.4:
        return "moderate"
    return "volatile"


def profile_diff(diff: SecretDiff) -> PathProfile:
    """Build a PathProfile from a single SecretDiff."""
    changed = len(diff.changed_keys)
    left_only = len(diff.only_in_left)
    right_only = len(diff.only_in_right)
    all_keys = set(diff.changed_keys) | set(diff.only_in_left) | set(diff.only_in_right)
    # include keys present in both (unchanged)
    unchanged_keys = (
        set(diff.left_data or {}) | set(diff.right_data or {})
    ) - all_keys
    total = changed + left_only + right_only + len(unchanged_keys)
    diff_count = changed + left_only + right_only
    volatility = diff_count / total if total > 0 else 0.0
    return PathProfile(
        path=diff.path,
        total_keys=total,
        changed_keys=changed,
        only_in_left=left_only,
        only_in_right=right_only,
        volatility=volatility,
        category=_category(volatility),
    )


def profile_diffs(diffs: List[SecretDiff]) -> List[PathProfile]:
    """Return profiles sorted by volatility descending."""
    profiles = [profile_diff(d) for d in diffs]
    profiles.sort(key=lambda p: p.volatility, reverse=True)
    return profiles
