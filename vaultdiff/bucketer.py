"""Bucketer: assign secret diffs into named time-window or size buckets."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from vaultdiff.differ import SecretDiff


@dataclass
class BucketRule:
    name: str
    max_changed_keys: Optional[int] = None
    max_total_keys: Optional[int] = None
    path_prefix: Optional[str] = None

    def matches(self, diff: SecretDiff) -> bool:
        if self.path_prefix and not diff.path.startswith(self.path_prefix):
            return False
        changed = len(diff.changed_keys) + len(diff.only_in_left) + len(diff.only_in_right)
        total = changed  # approximate
        if self.max_changed_keys is not None and changed > self.max_changed_keys:
            return False
        if self.max_total_keys is not None and total > self.max_total_keys:
            return False
        return True


@dataclass
class BucketConfig:
    rules: List[BucketRule] = field(default_factory=list)
    default_bucket: str = "default"

    @classmethod
    def from_dict(cls, data: dict) -> "BucketConfig":
        rules = [
            BucketRule(
                name=r["name"],
                max_changed_keys=r.get("max_changed_keys"),
                max_total_keys=r.get("max_total_keys"),
                path_prefix=r.get("path_prefix"),
            )
            for r in data.get("rules", [])
        ]
        return cls(rules=rules, default_bucket=data.get("default_bucket", "default"))


@dataclass
class Bucket:
    name: str
    diffs: List[SecretDiff] = field(default_factory=list)

    @property
    def total(self) -> int:
        return len(self.diffs)

    def to_dict(self) -> dict:
        return {"name": self.name, "total": self.total, "paths": [d.path for d in self.diffs]}


@dataclass
class BucketReport:
    buckets: Dict[str, Bucket] = field(default_factory=dict)

    @property
    def total_paths(self) -> int:
        return sum(b.total for b in self.buckets.values())

    def to_dict(self) -> dict:
        return {
            "total_paths": self.total_paths,
            "buckets": {name: b.to_dict() for name, b in self.buckets.items()},
        }


def bucket_diffs(diffs: List[SecretDiff], config: BucketConfig) -> BucketReport:
    report = BucketReport()
    for diff in diffs:
        assigned = False
        for rule in config.rules:
            if rule.matches(diff):
                if rule.name not in report.buckets:
                    report.buckets[rule.name] = Bucket(name=rule.name)
                report.buckets[rule.name].diffs.append(diff)
                assigned = True
                break
        if not assigned:
            if config.default_bucket not in report.buckets:
                report.buckets[config.default_bucket] = Bucket(name=config.default_bucket)
            report.buckets[config.default_bucket].diffs.append(diff)
    return report
