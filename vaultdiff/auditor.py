"""Audit logging for vaultdiff operations."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

from vaultdiff.differ import SecretDiff

logger = logging.getLogger(__name__)


@dataclass
class AuditEntry:
    timestamp: str
    path: str
    left_addr: str
    right_addr: str
    changed_keys: List[str] = field(default_factory=list)
    only_in_left: List[str] = field(default_factory=list)
    only_in_right: List[str] = field(default_factory=list)
    has_differences: bool = False

    def to_dict(self) -> dict:
        return asdict(self)


class Auditor:
    """Records audit entries for each compared secret path."""

    def __init__(self, left_addr: str, right_addr: str, output_path: Optional[str] = None):
        self.left_addr = left_addr
        self.right_addr = right_addr
        self.output_path = output_path
        self._entries: List[AuditEntry] = []

    def record(self, path: str, diff: SecretDiff) -> AuditEntry:
        """Record a diff result as an audit entry."""
        entry = AuditEntry(
            timestamp=datetime.now(timezone.utc).isoformat(),
            path=path,
            left_addr=self.left_addr,
            right_addr=self.right_addr,
            changed_keys=[k for k, _ in diff.changed],
            only_in_left=list(diff.only_in_left.keys()),
            only_in_right=list(diff.only_in_right.keys()),
            has_differences=diff.has_differences(),
        )
        self._entries.append(entry)
        logger.debug("Recorded audit entry for path: %s", path)
        return entry

    def entries(self) -> List[AuditEntry]:
        return list(self._entries)

    def summary(self) -> dict:
        total = len(self._entries)
        differing = sum(1 for e in self._entries if e.has_differences)
        return {
            "total_paths": total,
            "paths_with_differences": differing,
            "clean_paths": total - differing,
        }

    def write(self) -> None:
        """Write audit log to output_path as newline-delimited JSON."""
        if not self.output_path:
            raise ValueError("No output_path configured for auditor")
        path = Path(self.output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as fh:
            for entry in self._entries:
                fh.write(json.dumps(entry.to_dict()) + "\n")
        logger.info("Audit log written to %s (%d entries)", self.output_path, len(self._entries))
