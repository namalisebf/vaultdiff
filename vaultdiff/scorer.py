"""Scoring module: assigns a risk score to a set of SecretDiff results."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List

from vaultdiff.differ import SecretDiff

# Weights for each change category
_WEIGHT_CHANGED = 3
_WEIGHT_ONLY_IN_LEFT = 2   # key removed from right / destination
_WEIGHT_ONLY_IN_RIGHT = 1  # key added in right / destination


@dataclass
class PathScore:
    path: str
    changed_keys: int
    only_in_left: int
    only_in_right: int
    score: int

    def to_dict(self) -> dict:
        return {
            "path": self.path,
            "changed_keys": self.changed_keys,
            "only_in_left": self.only_in_left,
            "only_in_right": self.only_in_right,
            "score": self.score,
        }


@dataclass
class ScoreReport:
    path_scores: List[PathScore] = field(default_factory=list)
    total_score: int = 0

    def to_dict(self) -> dict:
        return {
            "total_score": self.total_score,
            "paths": [ps.to_dict() for ps in self.path_scores],
        }


def score_diff(path: str, diff: SecretDiff) -> PathScore:
    """Compute a risk score for a single secret path diff."""
    changed = len(diff.changed_keys)
    left_only = len(diff.only_in_left)
    right_only = len(diff.only_in_right)
    score = (
        changed * _WEIGHT_CHANGED
        + left_only * _WEIGHT_ONLY_IN_LEFT
        + right_only * _WEIGHT_ONLY_IN_RIGHT
    )
    return PathScore(
        path=path,
        changed_keys=changed,
        only_in_left=left_only,
        only_in_right=right_only,
        score=score,
    )


def score_diffs(diffs: dict[str, SecretDiff]) -> ScoreReport:
    """Compute a ScoreReport across multiple paths.

    Args:
        diffs: mapping of vault path -> SecretDiff

    Returns:
        ScoreReport with per-path scores and an aggregated total.
    """
    path_scores = [score_diff(path, diff) for path, diff in diffs.items()]
    total = sum(ps.score for ps in path_scores)
    return ScoreReport(path_scores=path_scores, total_score=total)
