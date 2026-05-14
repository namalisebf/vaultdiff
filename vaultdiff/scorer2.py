"""Path change scorer with configurable key weights."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List

from vaultdiff.differ import SecretDiff


_DEFAULT_WEIGHTS: Dict[str, float] = {
    "changed": 3.0,
    "only_in_left": 1.0,
    "only_in_right": 1.0,
}


@dataclass
class WeightedScoreConfig:
    weights: Dict[str, float] = field(default_factory=lambda: dict(_DEFAULT_WEIGHTS))

    @classmethod
    def from_dict(cls, data: dict) -> "WeightedScoreConfig":
        weights = dict(_DEFAULT_WEIGHTS)
        weights.update(data.get("weights", {}))
        return cls(weights=weights)


@dataclass
class ScoredEntry:
    path: str
    changed_keys: int
    only_in_left: int
    only_in_right: int
    score: float

    def to_dict(self) -> dict:
        return {
            "path": self.path,
            "changed_keys": self.changed_keys,
            "only_in_left": self.only_in_left,
            "only_in_right": self.only_in_right,
            "score": self.score,
        }


@dataclass
class WeightedScoreReport:
    entries: List[ScoredEntry] = field(default_factory=list)

    @property
    def total_score(self) -> float:
        return sum(e.score for e in self.entries)

    def to_dict(self) -> dict:
        return {
            "total_score": self.total_score,
            "entries": [e.to_dict() for e in self.entries],
        }


def score_diffs_weighted(
    diffs: List[SecretDiff],
    config: WeightedScoreConfig | None = None,
) -> WeightedScoreReport:
    if config is None:
        config = WeightedScoreConfig()
    w = config.weights
    entries: List[ScoredEntry] = []
    for d in diffs:
        changed = len(d.changed_keys)
        left = len(d.only_in_left)
        right = len(d.only_in_right)
        score = (
            changed * w.get("changed", 3.0)
            + left * w.get("only_in_left", 1.0)
            + right * w.get("only_in_right", 1.0)
        )
        entries.append(
            ScoredEntry(
                path=d.path,
                changed_keys=changed,
                only_in_left=left,
                only_in_right=right,
                score=score,
            )
        )
    entries.sort(key=lambda e: e.score, reverse=True)
    return WeightedScoreReport(entries=entries)
