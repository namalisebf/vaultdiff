"""Partition diffs into named buckets based on path depth or prefix segments."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from vaultdiff.differ import SecretDiff


@dataclass
class PartitionConfig:
    depth: int = 1  # number of path segments to use as partition key
    separator: str = "/"
    default_partition: str = "other"

    @classmethod
    def from_dict(cls, data: dict) -> "PartitionConfig":
        return cls(
            depth=int(data.get("depth", 1)),
            separator=data.get("separator", "/"),
            default_partition=data.get("default_partition", "other"),
        )


@dataclass
class Partition:
    name: str
    diffs: List[SecretDiff] = field(default_factory=list)

    @property
    def total(self) -> int:
        return len(self.diffs)

    @property
    def dirty(self) -> int:
        return sum(1 for d in self.diffs if d.has_differences())

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "total": self.total,
            "dirty": self.dirty,
            "clean": self.total - self.dirty,
        }


@dataclass
class PartitionReport:
    partitions: List[Partition]

    @property
    def total_partitions(self) -> int:
        return len(self.partitions)

    def to_dict(self) -> dict:
        return {
            "total_partitions": self.total_partitions,
            "partitions": [p.to_dict() for p in self.partitions],
        }


def _partition_key(path: str, depth: int, separator: str, default: str) -> str:
    parts = path.strip(separator).split(separator)
    key_parts = parts[:depth]
    return separator.join(key_parts) if key_parts else default


def partition_diffs(
    diffs: List[SecretDiff],
    config: Optional[PartitionConfig] = None,
) -> PartitionReport:
    if config is None:
        config = PartitionConfig()

    buckets: Dict[str, Partition] = {}
    for diff in diffs:
        key = _partition_key(
            diff.path, config.depth, config.separator, config.default_partition
        )
        if key not in buckets:
            buckets[key] = Partition(name=key)
        buckets[key].diffs.append(diff)

    ordered = sorted(buckets.values(), key=lambda p: p.name)
    return PartitionReport(partitions=ordered)
