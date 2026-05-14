"""Renamer: apply path rename rules to a list of SecretDiff results."""
from __future__ import annotations

import fnmatch
import re
from dataclasses import dataclass, field
from typing import List, Optional

from vaultdiff.differ import SecretDiff


@dataclass
class RenameRule:
    pattern: str
    replacement: str
    mode: str = "prefix"  # prefix | glob | regex

    def apply(self, path: str) -> Optional[str]:
        if self.mode == "prefix":
            if path.startswith(self.pattern):
                return self.replacement + path[len(self.pattern):]
        elif self.mode == "glob":
            if fnmatch.fnmatch(path, self.pattern):
                return re.sub(
                    fnmatch.translate(self.pattern).rstrip("\\Z$").rstrip("(?s:").rstrip(")"),
                    self.replacement,
                    path,
                )
        elif self.mode == "regex":
            m = re.search(self.pattern, path)
            if m:
                return re.sub(self.pattern, self.replacement, path)
        return None


@dataclass
class RenameConfig:
    rules: List[RenameRule] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict) -> "RenameConfig":
        rules = [
            RenameRule(
                pattern=r["pattern"],
                replacement=r["replacement"],
                mode=r.get("mode", "prefix"),
            )
            for r in data.get("rules", [])
        ]
        return cls(rules=rules)


@dataclass
class RenamedDiff:
    original_path: str
    renamed_path: str
    diff: SecretDiff
    rule_applied: bool

    def to_dict(self) -> dict:
        return {
            "original_path": self.original_path,
            "renamed_path": self.renamed_path,
            "rule_applied": self.rule_applied,
            "changed_keys": list(self.diff.changed_keys),
            "only_in_left": list(self.diff.only_in_left),
            "only_in_right": list(self.diff.only_in_right),
        }


def rename_diffs(diffs: List[SecretDiff], config: RenameConfig) -> List[RenamedDiff]:
    results: List[RenamedDiff] = []
    for diff in diffs:
        renamed = None
        for rule in config.rules:
            renamed = rule.apply(diff.path)
            if renamed is not None:
                break
        results.append(
            RenamedDiff(
                original_path=diff.path,
                renamed_path=renamed if renamed is not None else diff.path,
                diff=diff,
                rule_applied=renamed is not None,
            )
        )
    return results
