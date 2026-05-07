"""Digester: compute and compare cryptographic digests of secret paths."""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from vaultdiff.differ import SecretDiff


def _digest_secret(data: Dict[str, str]) -> str:
    """Return a stable SHA-256 hex digest of a key/value mapping."""
    canonical = json.dumps(data, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode()).hexdigest()


@dataclass
class DigestEntry:
    path: str
    left_digest: Optional[str]
    right_digest: Optional[str]

    @property
    def match(self) -> bool:
        return self.left_digest == self.right_digest

    def to_dict(self) -> dict:
        return {
            "path": self.path,
            "left_digest": self.left_digest,
            "right_digest": self.right_digest,
            "match": self.match,
        }


@dataclass
class DigestReport:
    entries: List[DigestEntry] = field(default_factory=list)

    @property
    def all_match(self) -> bool:
        return all(e.match for e in self.entries)

    @property
    def mismatched_paths(self) -> List[str]:
        return [e.path for e in self.entries if not e.match]

    def to_dict(self) -> dict:
        return {
            "all_match": self.all_match,
            "mismatched_paths": self.mismatched_paths,
            "entries": [e.to_dict() for e in self.entries],
        }


def digest_diffs(diffs: List[SecretDiff]) -> DigestReport:
    """Produce a DigestReport from a list of SecretDiff objects."""
    entries: List[DigestEntry] = []
    for diff in diffs:
        left_digest = _digest_secret(diff.left_data) if diff.left_data is not None else None
        right_digest = _digest_secret(diff.right_data) if diff.right_data is not None else None
        entries.append(DigestEntry(
            path=diff.path,
            left_digest=left_digest,
            right_digest=right_digest,
        ))
    return DigestReport(entries=entries)
