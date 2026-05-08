"""Segment secret diffs into named buckets based on path depth or prefix rules."""
from __future__ import annotations

from dataclasses import dataclass, field
from fnmatch import fnmatch
from typing import Dict, List, Optional

from vaultdiff.differ import SecretDiff


@dataclass
class SegmentRule:
    name: str
    prefix: Optional[str] = None
    glob: Optional[str] = None

    def matches(self, path: str) -> bool:
        if self.prefix and path.startswith(self.prefix):
            return True
        if self.glob and fnmatch(path, self.glob):
            return True
        return False


@dataclass
class SegmentConfig:
    rules: List[SegmentRule] = field(default_factory=list)
    default_segment: str = "default"

    @classmethod
    def from_dict(cls, data: dict) -> "SegmentConfig":
        rules = [
            SegmentRule(
                name=r["name"],
                prefix=r.get("prefix"),
                glob=r.get("glob"),
            )
            for r in data.get("rules", [])
        ]
        return cls(
            rules=rules,
            default_segment=data.get("default_segment", "default"),
        )


@dataclass
class Segment:
    name: str
    diffs: List[SecretDiff] = field(default_factory=list)

    @property
    def total(self) -> int:
        return len(self.diffs)

    @property
    def dirty(self) -> int:
        return sum(1 for d in self.diffs if d.has_differences)

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "total": self.total,
            "dirty": self.dirty,
            "paths": [d.path for d in self.diffs],
        }


@dataclass
class SegmentReport:
    segments: Dict[str, Segment] = field(default_factory=dict)

    @property
    def total_paths(self) -> int:
        return sum(s.total for s in self.segments.values())

    def to_dict(self) -> dict:
        return {
            "total_paths": self.total_paths,
            "segments": {name: seg.to_dict() for name, seg in self.segments.items()},
        }


def segment_diffs(diffs: List[SecretDiff], config: Optional[SegmentConfig] = None) -> SegmentReport:
    if config is None:
        config = SegmentConfig()

    report = SegmentReport()

    for diff in diffs:
        matched = config.default_segment
        for rule in config.rules:
            if rule.matches(diff.path):
                matched = rule.name
                break
        if matched not in report.segments:
            report.segments[matched] = Segment(name=matched)
        report.segments[matched].diffs.append(diff)

    return report
