"""Rank secret paths by risk/change severity for prioritised review."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Dict, Any

from vaultdiff.differ import SecretDiff
from vaultdiff.scorer import score_diff

# Weight multipliers applied on top of the raw score
_TIER_WEIGHTS: Dict[str, float] = {
    "critical": 3.0,
    "high": 2.0,
    "medium": 1.5,
    "low": 1.0,
}


@dataclass
class RankedPath:
    path: str
    raw_score: float
    tier: str
    weighted_score: float
    change_summary: Dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "path": self.path,
            "raw_score": self.raw_score,
            "tier": self.tier,
            "weighted_score": self.weighted_score,
            "change_summary": self.change_summary,
        }


def _classify_tier(raw_score: float) -> str:
    if raw_score >= 20:
        return "critical"
    if raw_score >= 10:
        return "high"
    if raw_score >= 4:
        return "medium"
    return "low"


def rank_diffs(diffs: List[SecretDiff]) -> List[RankedPath]:
    """Return *diffs* sorted descending by weighted risk score."""
    ranked: List[RankedPath] = []
    for diff in diffs:
        report = score_diff(diff)
        raw = report.total_score
        tier = _classify_tier(raw)
        weighted = raw * _tier_weights.get(tier, 1.0)
        summary = {
            "changed": len(diff.changed_keys),
            "only_in_left": len(diff.only_in_left),
            "only_in_right": len(diff.only_in_right),
        }
        ranked.append(
            RankedPath(
                path=diff.path,
                raw_score=raw,
                tier=tier,
                weighted_score=weighted,
                change_summary=summary,
            )
        )
    ranked.sort(key=lambda r: r.weighted_score, reverse=True)
    return ranked
