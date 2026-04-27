"""Baseline snapshot support for vaultdiff.

Allows saving a snapshot of secret diffs to a JSON file and comparing
future diffs against that baseline to detect regressions or drift.
"""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass
from typing import Dict, List, Optional

from vaultdiff.differ import SecretDiff


@dataclass
class BaselineEntry:
    path: str
    changed_keys: List[str]
    only_in_left: List[str]
    only_in_right: List[str]

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_diff(cls, path: str, diff: SecretDiff) -> "BaselineEntry":
        return cls(
            path=path,
            changed_keys=sorted(diff.changed_keys.keys()),
            only_in_left=sorted(diff.only_in_left),
            only_in_right=sorted(diff.only_in_right),
        )


def save_baseline(path: str, entries: List[BaselineEntry]) -> None:
    """Serialize baseline entries to a JSON file."""
    data = [e.to_dict() for e in entries]
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2)


def load_baseline(path: str) -> List[BaselineEntry]:
    """Load baseline entries from a JSON file."""
    if not os.path.exists(path):
        raise FileNotFoundError(f"Baseline file not found: {path}")
    with open(path, "r", encoding="utf-8") as fh:
        data = json.load(fh)
    return [
        BaselineEntry(
            path=item["path"],
            changed_keys=item["changed_keys"],
            only_in_left=item["only_in_left"],
            only_in_right=item["only_in_right"],
        )
        for item in data
    ]


def compare_to_baseline(
    current: Dict[str, SecretDiff],
    baseline: List[BaselineEntry],
) -> Dict[str, List[str]]:
    """Return new issues not present in the baseline, keyed by path."""
    baseline_map: Dict[str, BaselineEntry] = {e.path: e for e in baseline}
    regressions: Dict[str, List[str]] = {}

    for path, diff in current.items():
        entry = baseline_map.get(path)
        new_issues: List[str] = []

        current_changed = set(diff.changed_keys.keys())
        current_left = set(diff.only_in_left)
        current_right = set(diff.only_in_right)

        if entry is None:
            if current_changed or current_left or current_right:
                new_issues.append("path not in baseline")
        else:
            for key in current_changed - set(entry.changed_keys):
                new_issues.append(f"new changed key: {key}")
            for key in current_left - set(entry.only_in_left):
                new_issues.append(f"new key only in left: {key}")
            for key in current_right - set(entry.only_in_right):
                new_issues.append(f"new key only in right: {key}")

        if new_issues:
            regressions[path] = new_issues

    return regressions
