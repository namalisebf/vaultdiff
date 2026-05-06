"""splitter.py — split a list of SecretDiff results into named buckets by path prefix."""
from __future__ import annotations

from dataclasses import dataclass, field
from fnmatch import fnmatch
from typing import Dict, List, Optional

from vaultdiff.differ import SecretDiff


@dataclass
class SplitRule:
    bucket: str
    prefix: Optional[str] = None
    glob: Optional[str] = None

    def matches(self, path: str) -> bool:
        if self.prefix and path.startswith(self.prefix):
            return True
        if self.glob and fnmatch(path, self.glob):
            return True
        return False


@dataclass
class SplitConfig:
    rules: List[SplitRule] = field(default_factory=list)
    default_bucket: str = "default"

    @classmethod
    def from_dict(cls, data: dict) -> "SplitConfig":
        rules = [
            SplitRule(
                bucket=r["bucket"],
                prefix=r.get("prefix"),
                glob=r.get("glob"),
            )
            for r in data.get("rules", [])
        ]
        return cls(
            rules=rules,
            default_bucket=data.get("default_bucket", "default"),
        )


@dataclass
class SplitReport:
    buckets: Dict[str, List[SecretDiff]] = field(default_factory=dict)

    def bucket_names(self) -> List[str]:
        return sorted(self.buckets.keys())

    def total(self) -> int:
        return sum(len(v) for v in self.buckets.values())

    def to_dict(self) -> dict:
        return {
            bucket: [
                {"path": d.path, "has_differences": d.has_differences()}
                for d in diffs
            ]
            for bucket, diffs in self.buckets.items()
        }


def split_diffs(diffs: List[SecretDiff], config: SplitConfig) -> SplitReport:
    """Assign each SecretDiff to the first matching bucket, or the default bucket."""
    report = SplitReport()
    for diff in diffs:
        assigned = False
        for rule in config.rules:
            if rule.matches(diff.path):
                report.buckets.setdefault(rule.bucket, []).append(diff)
                assigned = True
                break
        if not assigned:
            report.buckets.setdefault(config.default_bucket, []).append(diff)
    return report
