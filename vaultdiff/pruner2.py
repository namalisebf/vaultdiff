"""Pruner2: drop diffs that fall below a minimum score threshold."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

from vaultdiff.differ import SecretDiff


@dataclass
class ScorePruneConfig:
    min_score: float = 0.0
    drop_clean: bool = False
    max_paths: Optional[int] = None

    @classmethod
    def from_dict(cls, data: dict) -> "ScorePruneConfig":
        return cls(
            min_score=float(data.get("min_score", 0.0)),
            drop_clean=bool(data.get("drop_clean", False)),
            max_paths=data.get("max_paths"),
        )


@dataclass
class ScorePruneReport:
    kept: List[SecretDiff] = field(default_factory=list)
    dropped: List[SecretDiff] = field(default_factory=list)

    @property
    def total_dropped(self) -> int:
        return len(self.dropped)

    @property
    def total_kept(self) -> int:
        return len(self.kept)

    def to_dict(self) -> dict:
        return {
            "total_kept": self.total_kept,
            "total_dropped": self.total_dropped,
            "kept_paths": [d.path for d in self.kept],
            "dropped_paths": [d.path for d in self.dropped],
        }


def _score_diff(diff: SecretDiff) -> float:
    """Simple scoring: changed keys weighted 2x, added/removed weighted 1x."""
    return (
        len(diff.changed_keys) * 2.0
        + len(diff.only_in_left) * 1.0
        + len(diff.only_in_right) * 1.0
    )


def score_prune(diffs: List[SecretDiff], config: Optional[ScorePruneConfig] = None) -> ScorePruneReport:
    if config is None:
        config = ScorePruneConfig()

    report = ScorePruneReport()
    for diff in diffs:
        score = _score_diff(diff)
        has_diff = diff.has_differences()
        if config.drop_clean and not has_diff:
            report.dropped.append(diff)
        elif score < config.min_score:
            report.dropped.append(diff)
        else:
            report.kept.append(diff)

    if config.max_paths is not None:
        over = report.kept[config.max_paths:]
        report.kept = report.kept[: config.max_paths]
        report.dropped.extend(over)

    return report
