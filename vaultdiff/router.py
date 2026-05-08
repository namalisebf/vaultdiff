"""Route secret diffs to named destinations based on path rules."""
from __future__ import annotations

import fnmatch
import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from vaultdiff.differ import SecretDiff


@dataclass
class RouteRule:
    destination: str
    prefix: Optional[str] = None
    glob: Optional[str] = None
    regex: Optional[str] = None

    def matches(self, path: str) -> bool:
        if self.prefix and path.startswith(self.prefix):
            return True
        if self.glob and fnmatch.fnmatch(path, self.glob):
            return True
        if self.regex and re.search(self.regex, path):
            return True
        return False


@dataclass
class RouteConfig:
    rules: List[RouteRule] = field(default_factory=list)
    default_destination: str = "default"

    @classmethod
    def from_dict(cls, data: dict) -> "RouteConfig":
        rules = [
            RouteRule(
                destination=r["destination"],
                prefix=r.get("prefix"),
                glob=r.get("glob"),
                regex=r.get("regex"),
            )
            for r in data.get("rules", [])
        ]
        return cls(
            rules=rules,
            default_destination=data.get("default_destination", "default"),
        )


@dataclass
class RouteReport:
    routes: Dict[str, List[SecretDiff]] = field(default_factory=dict)

    @property
    def destinations(self) -> List[str]:
        return sorted(self.routes.keys())

    def diffs_for(self, destination: str) -> List[SecretDiff]:
        return self.routes.get(destination, [])

    def to_dict(self) -> dict:
        return {
            dest: [d.path for d in diffs]
            for dest, diffs in self.routes.items()
        }


def route_diffs(diffs: List[SecretDiff], config: RouteConfig) -> RouteReport:
    report = RouteReport()
    for diff in diffs:
        destination = config.default_destination
        for rule in config.rules:
            if rule.matches(diff.path):
                destination = rule.destination
                break
        report.routes.setdefault(destination, []).append(diff)
    return report
