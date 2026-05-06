"""Index secret paths by key presence and value fingerprint for fast lookup."""
from __future__ import annotations

from dataclasses import dataclass, field
from hashlib import sha256
from typing import Dict, List, Optional

from vaultdiff.differ import SecretDiff


def _fingerprint(value: str) -> str:
    """Return a short SHA-256 hex digest for a secret value."""
    return sha256(value.encode()).hexdigest()[:12]


@dataclass
class IndexEntry:
    path: str
    keys: List[str] = field(default_factory=list)
    fingerprints: Dict[str, str] = field(default_factory=dict)  # key -> fingerprint

    def to_dict(self) -> dict:
        return {
            "path": self.path,
            "keys": self.keys,
            "fingerprints": self.fingerprints,
        }


@dataclass
class SecretIndex:
    entries: List[IndexEntry] = field(default_factory=list)

    # ---- derived lookups ------------------------------------------------

    def paths_with_key(self, key: str) -> List[str]:
        """Return all paths that contain *key*."""
        return [e.path for e in self.entries if key in e.keys]

    def paths_with_fingerprint(self, key: str, fingerprint: str) -> List[str]:
        """Return paths where *key* has the given value fingerprint."""
        return [
            e.path
            for e in self.entries
            if e.fingerprints.get(key) == fingerprint
        ]

    def to_dict(self) -> dict:
        return {"entries": [e.to_dict() for e in self.entries]}


def build_index(
    diffs: List[SecretDiff],
    side: str = "left",
) -> SecretIndex:
    """Build a :class:`SecretIndex` from a list of diffs.

    *side* selects which environment's values are fingerprinted
    (``"left"`` or ``"right"``).  Keys present only on the opposite
    side are included in the key list but carry no fingerprint.
    """
    if side not in ("left", "right"):
        raise ValueError(f"side must be 'left' or 'right', got {side!r}")

    entries: List[IndexEntry] = []

    for diff in diffs:
        all_keys: List[str] = list(
            dict.fromkeys(
                list(diff.changed.keys())
                + list(diff.only_in_left.keys())
                + list(diff.only_in_right.keys())
            )
        )

        fingerprints: Dict[str, str] = {}
        for key, change in diff.changed.items():
            value = change.left if side == "left" else change.right
            if value is not None:
                fingerprints[key] = _fingerprint(str(value))

        side_only = diff.only_in_left if side == "left" else diff.only_in_right
        for key, value in side_only.items():
            if value is not None:
                fingerprints[key] = _fingerprint(str(value))

        entries.append(IndexEntry(path=diff.path, keys=all_keys, fingerprints=fingerprints))

    return SecretIndex(entries=entries)
