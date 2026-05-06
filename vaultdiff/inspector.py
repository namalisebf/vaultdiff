"""Inspector: surface per-key metadata (type, length, entropy) across diff results."""
from __future__ import annotations

import math
import string
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from vaultdiff.differ import SecretDiff


def _shannon_entropy(value: str) -> float:
    """Compute Shannon entropy (bits) of a string."""
    if not value:
        return 0.0
    freq: Dict[str, int] = {}
    for ch in value:
        freq[ch] = freq.get(ch, 0) + 1
    n = len(value)
    return -sum((c / n) * math.log2(c / n) for c in freq.values())


def _value_type(value: str) -> str:
    if not value:
        return "empty"
    if value.isdigit():
        return "numeric"
    if all(c in string.hexdigits for c in value):
        return "hex"
    if all(c in (string.ascii_letters + string.digits + "+/=") for c in value):
        return "base64_candidate"
    return "string"


@dataclass
class KeyInspection:
    key: str
    present_in_left: bool
    present_in_right: bool
    left_length: Optional[int]
    right_length: Optional[int]
    left_entropy: Optional[float]
    right_entropy: Optional[float]
    left_type: Optional[str]
    right_type: Optional[str]

    def to_dict(self) -> dict:
        return {
            "key": self.key,
            "present_in_left": self.present_in_left,
            "present_in_right": self.present_in_right,
            "left_length": self.left_length,
            "right_length": self.right_length,
            "left_entropy": round(self.left_entropy, 4) if self.left_entropy is not None else None,
            "right_entropy": round(self.right_entropy, 4) if self.right_entropy is not None else None,
            "left_type": self.left_type,
            "right_type": self.right_type,
        }


@dataclass
class PathInspection:
    path: str
    keys: List[KeyInspection] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {"path": self.path, "keys": [k.to_dict() for k in self.keys]}


def inspect_diff(diff: SecretDiff) -> PathInspection:
    """Produce a PathInspection from a SecretDiff."""
    inspections: List[KeyInspection] = []

    all_keys = (
        set(diff.changed_keys)
        | set(diff.only_in_left)
        | set(diff.only_in_right)
    )

    left_data = diff.left_data or {}
    right_data = diff.right_data or {}

    for key in sorted(all_keys):
        lv = left_data.get(key)
        rv = right_data.get(key)
        inspections.append(KeyInspection(
            key=key,
            present_in_left=lv is not None,
            present_in_right=rv is not None,
            left_length=len(str(lv)) if lv is not None else None,
            right_length=len(str(rv)) if rv is not None else None,
            left_entropy=_shannon_entropy(str(lv)) if lv is not None else None,
            right_entropy=_shannon_entropy(str(rv)) if rv is not None else None,
            left_type=_value_type(str(lv)) if lv is not None else None,
            right_type=_value_type(str(rv)) if rv is not None else None,
        ))

    return PathInspection(path=diff.path, keys=inspections)


def inspect_diffs(diffs: List[SecretDiff]) -> List[PathInspection]:
    return [inspect_diff(d) for d in diffs]
