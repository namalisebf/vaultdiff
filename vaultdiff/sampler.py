"""sampler.py — randomly sample a subset of secret paths for spot-check diffing."""
from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import List, Optional

from vaultdiff.differ import SecretDiff


@dataclass
class SampleConfig:
    seed: Optional[int] = None
    max_paths: int = 10
    fraction: Optional[float] = None  # 0.0–1.0; takes priority over max_paths when set

    @classmethod
    def from_dict(cls, data: dict) -> "SampleConfig":
        return cls(
            seed=data.get("seed"),
            max_paths=int(data.get("max_paths", 10)),
            fraction=float(data["fraction"]) if "fraction" in data else None,
        )


@dataclass
class SampleReport:
    selected: List[SecretDiff]
    total_available: int
    sample_size: int
    seed: Optional[int]

    @property
    def coverage(self) -> float:
        if self.total_available == 0:
            return 0.0
        return self.sample_size / self.total_available

    def to_dict(self) -> dict:
        return {
            "total_available": self.total_available,
            "sample_size": self.sample_size,
            "coverage": round(self.coverage, 4),
            "seed": self.seed,
            "paths": [d.path for d in self.selected],
        }


def sample_diffs(
    diffs: List[SecretDiff],
    config: Optional[SampleConfig] = None,
) -> SampleReport:
    """Return a random subset of *diffs* according to *config*."""
    if config is None:
        config = SampleConfig()

    rng = random.Random(config.seed)
    total = len(diffs)

    if config.fraction is not None:
        if not (0.0 <= config.fraction <= 1.0):
            raise ValueError("fraction must be between 0.0 and 1.0")
        k = max(1, round(total * config.fraction)) if total else 0
    else:
        k = min(config.max_paths, total)

    selected = rng.sample(diffs, k) if k and diffs else []

    return SampleReport(
        selected=selected,
        total_available=total,
        sample_size=len(selected),
        seed=config.seed,
    )
