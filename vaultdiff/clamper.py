"""Clamper: constrain diff results to a bounded value range for numeric secret values."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

from vaultdiff.differ import SecretDiff


@dataclass
class ClampConfig:
    min_changed_keys: int = 0
    max_changed_keys: Optional[int] = None
    min_only_in_left: int = 0
    max_only_in_left: Optional[int] = None
    min_only_in_right: int = 0
    max_only_in_right: Optional[int] = None

    @classmethod
    def from_dict(cls, data: dict) -> "ClampConfig":
        return cls(
            min_changed_keys=int(data.get("min_changed_keys", 0)),
            max_changed_keys=_optional_int(data.get("max_changed_keys")),
            min_only_in_left=int(data.get("min_only_in_left", 0)),
            max_only_in_left=_optional_int(data.get("max_only_in_left")),
            min_only_in_right=int(data.get("min_only_in_right", 0)),
            max_only_in_right=_optional_int(data.get("max_only_in_right")),
        )


def _optional_int(value) -> Optional[int]:
    if value is None:
        return None
    return int(value)


def _clamp(value: int, lo: int, hi: Optional[int]) -> bool:
    if value < lo:
        return False
    if hi is not None and value > hi:
        return False
    return True


@dataclass
class ClampReport:
    kept: List[SecretDiff] = field(default_factory=list)
    dropped: List[SecretDiff] = field(default_factory=list)

    @property
    def total_kept(self) -> int:
        return len(self.kept)

    @property
    def total_dropped(self) -> int:
        return len(self.dropped)

    def to_dict(self) -> dict:
        return {
            "total_kept": self.total_kept,
            "total_dropped": self.total_dropped,
            "kept_paths": [d.path for d in self.kept],
            "dropped_paths": [d.path for d in self.dropped],
        }


def clamp_diffs(diffs: List[SecretDiff], config: ClampConfig) -> ClampReport:
    """Filter diffs whose change counts fall within the configured bounds."""
    report = ClampReport()
    for diff in diffs:
        n_changed = len(diff.changed)
        n_left = len(diff.only_in_left)
        n_right = len(diff.only_in_right)
        if (
            _clamp(n_changed, config.min_changed_keys, config.max_changed_keys)
            and _clamp(n_left, config.min_only_in_left, config.max_only_in_left)
            and _clamp(n_right, config.min_only_in_right, config.max_only_in_right)
        ):
            report.kept.append(diff)
        else:
            report.dropped.append(diff)
    return report
