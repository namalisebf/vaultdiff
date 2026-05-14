"""Batch processing of secret diffs into fixed-size chunks."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

from vaultdiff.differ import SecretDiff


@dataclass
class BatchConfig:
    size: int = 10
    skip_clean: bool = False

    @classmethod
    def from_dict(cls, data: dict) -> "BatchConfig":
        return cls(
            size=int(data.get("size", 10)),
            skip_clean=bool(data.get("skip_clean", False)),
        )


@dataclass
class Batch:
    index: int
    items: List[SecretDiff] = field(default_factory=list)

    @property
    def total(self) -> int:
        return len(self.items)

    @property
    def dirty_count(self) -> int:
        return sum(1 for d in self.items if d.has_differences)

    def to_dict(self) -> dict:
        return {
            "index": self.index,
            "total": self.total,
            "dirty_count": self.dirty_count,
            "paths": [d.path for d in self.items],
        }


@dataclass
class BatchReport:
    batches: List[Batch] = field(default_factory=list)

    @property
    def total_batches(self) -> int:
        return len(self.batches)

    @property
    def total_paths(self) -> int:
        return sum(b.total for b in self.batches)

    def to_dict(self) -> dict:
        return {
            "total_batches": self.total_batches,
            "total_paths": self.total_paths,
            "batches": [b.to_dict() for b in self.batches],
        }


def batch_diffs(
    diffs: List[SecretDiff],
    config: Optional[BatchConfig] = None,
) -> BatchReport:
    cfg = config or BatchConfig()
    candidates = [
        d for d in diffs if not (cfg.skip_clean and not d.has_differences)
    ]
    batches: List[Batch] = []
    for i in range(0, len(candidates), cfg.size):
        chunk = candidates[i : i + cfg.size]
        batches.append(Batch(index=len(batches), items=chunk))
    return BatchReport(batches=batches)
