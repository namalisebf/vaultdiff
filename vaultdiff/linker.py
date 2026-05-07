"""linker.py — Cross-path dependency linking for secret diffs.

Identifies shared key names across multiple diff results and builds
a link map showing which paths share common key names, helping
operators spot cascading changes across environments.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from collections import defaultdict
from typing import Dict, List

from vaultdiff.differ import SecretDiff


@dataclass
class LinkedKey:
    key: str
    paths: List[str]

    @property
    def link_count(self) -> int:
        return len(self.paths)

    def to_dict(self) -> dict:
        return {
            "key": self.key,
            "paths": self.paths,
            "link_count": self.link_count,
        }


@dataclass
class LinkReport:
    linked_keys: List[LinkedKey] = field(default_factory=list)

    @property
    def total_shared_keys(self) -> int:
        return len(self.linked_keys)

    @property
    def total_affected_paths(self) -> int:
        paths: set = set()
        for lk in self.linked_keys:
            paths.update(lk.paths)
        return len(paths)

    def to_dict(self) -> dict:
        return {
            "total_shared_keys": self.total_shared_keys,
            "total_affected_paths": self.total_affected_paths,
            "linked_keys": [lk.to_dict() for lk in self.linked_keys],
        }


def build_link_report(diffs: List[SecretDiff], min_links: int = 2) -> LinkReport:
    """Build a LinkReport from a list of SecretDiff objects.

    A key is considered 'linked' when it appears (as changed, added, or
    removed) in at least *min_links* distinct secret paths.

    Args:
        diffs: List of SecretDiff results to analyse.
        min_links: Minimum number of paths a key must appear in to be
            included in the report. Defaults to 2.

    Returns:
        A LinkReport listing all shared keys and the paths they appear in.
    """
    key_to_paths: Dict[str, List[str]] = defaultdict(list)

    for diff in diffs:
        seen_keys: set = set()
        for entry in diff.changed:
            seen_keys.add(entry.key)
        for key in diff.only_in_left:
            seen_keys.add(key)
        for key in diff.only_in_right:
            seen_keys.add(key)
        for key in seen_keys:
            key_to_paths[key].append(diff.path)

    linked: List[LinkedKey] = [
        LinkedKey(key=k, paths=sorted(set(v)))
        for k, v in sorted(key_to_paths.items())
        if len(set(v)) >= min_links
    ]

    return LinkReport(linked_keys=linked)
