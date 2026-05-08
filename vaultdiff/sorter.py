"""Sort SecretDiff results by various criteria."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import List, Optional

from vaultdiff.differ import SecretDiff


class SortKey(str, Enum):
    PATH = "path"
    CHANGED_KEYS = "changed_keys"
    TOTAL_KEYS = "total_keys"
    DIFFERENCES = "differences"


@dataclass
class SortConfig:
    key: SortKey = SortKey.PATH
    reverse: bool = False

    @classmethod
    def from_dict(cls, data: dict) -> "SortConfig":
        key_str = data.get("key", SortKey.PATH.value)
        try:
            key = SortKey(key_str)
        except ValueError:
            key = SortKey.PATH
        return cls(
            key=key,
            reverse=bool(data.get("reverse", False)),
        )


@dataclass
class SortedReport:
    diffs: List[SecretDiff]
    key: SortKey
    reverse: bool

    @property
    def total_paths(self) -> int:
        return len(self.diffs)

    def to_dict(self) -> dict:
        return {
            "key": self.key.value,
            "reverse": self.reverse,
            "total_paths": self.total_paths,
            "paths": [d.path for d in self.diffs],
        }


def _sort_key_fn(key: SortKey):
    if key == SortKey.PATH:
        return lambda d: d.path
    if key == SortKey.CHANGED_KEYS:
        return lambda d: len(d.changed_keys)
    if key == SortKey.TOTAL_KEYS:
        left_keys = lambda d: len(d.only_in_left) + len(d.only_in_right) + len(d.changed_keys)  # noqa: E731
        return left_keys
    if key == SortKey.DIFFERENCES:
        return lambda d: len(d.only_in_left) + len(d.only_in_right) + len(d.changed_keys)
    return lambda d: d.path


def sort_diffs(
    diffs: List[SecretDiff],
    config: Optional[SortConfig] = None,
) -> SortedReport:
    if config is None:
        config = SortConfig()
    fn = _sort_key_fn(config.key)
    sorted_diffs = sorted(diffs, key=fn, reverse=config.reverse)
    return SortedReport(diffs=sorted_diffs, key=config.key, reverse=config.reverse)
