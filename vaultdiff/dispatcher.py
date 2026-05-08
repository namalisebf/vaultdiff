"""Dispatcher: route diffs to named handlers based on path patterns."""
from __future__ import annotations

import fnmatch
import re
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional

from vaultdiff.differ import SecretDiff


@dataclass
class DispatchRule:
    name: str
    pattern: str
    mode: str = "glob"  # glob | prefix | regex

    def matches(self, path: str) -> bool:
        if self.mode == "prefix":
            return path.startswith(self.pattern)
        if self.mode == "regex":
            return bool(re.search(self.pattern, path))
        return fnmatch.fnmatch(path, self.pattern)


@dataclass
class DispatchConfig:
    rules: List[DispatchRule] = field(default_factory=list)
    default_handler: str = "default"

    @classmethod
    def from_dict(cls, data: dict) -> "DispatchConfig":
        rules = [
            DispatchRule(
                name=r["name"],
                pattern=r["pattern"],
                mode=r.get("mode", "glob"),
            )
            for r in data.get("rules", [])
        ]
        return cls(
            rules=rules,
            default_handler=data.get("default_handler", "default"),
        )


Handler = Callable[[SecretDiff], None]


@dataclass
class DispatchReport:
    dispatched: Dict[str, List[SecretDiff]] = field(default_factory=dict)

    def handler_names(self) -> List[str]:
        return list(self.dispatched.keys())

    def to_dict(self) -> dict:
        return {
            name: [d.path for d in diffs]
            for name, diffs in self.dispatched.items()
        }


class Dispatcher:
    def __init__(self, config: DispatchConfig) -> None:
        self._config = config

    def dispatch(self, diffs: List[SecretDiff]) -> DispatchReport:
        report = DispatchReport()
        for diff in diffs:
            handler = self._resolve(diff.path)
            report.dispatched.setdefault(handler, []).append(diff)
        return report

    def _resolve(self, path: str) -> str:
        for rule in self._config.rules:
            if rule.matches(path):
                return rule.name
        return self._config.default_handler

    def run(self, diffs: List[SecretDiff], handlers: Dict[str, Handler]) -> None:
        report = self.dispatch(diffs)
        for name, bucket in report.dispatched.items():
            handler = handlers.get(name) or handlers.get(self._config.default_handler)
            if handler:
                for diff in bucket:
                    handler(diff)
