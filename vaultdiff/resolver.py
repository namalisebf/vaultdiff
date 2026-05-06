"""Resolver: resolve secret paths across multiple environments into a unified view."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from vaultdiff.vault_client import VaultClient


@dataclass
class ResolvedPath:
    path: str
    envs: Dict[str, Optional[Dict[str, str]]] = field(default_factory=dict)

    @property
    def present_in(self) -> List[str]:
        return [env for env, data in self.envs.items() if data is not None]

    @property
    def missing_from(self) -> List[str]:
        return [env for env, data in self.envs.items() if data is None]

    @property
    def is_consistent(self) -> bool:
        values = [frozenset(d.items()) for d in self.envs.values() if d is not None]
        return len(set(values)) <= 1

    def to_dict(self) -> dict:
        return {
            "path": self.path,
            "envs": {k: v for k, v in self.envs.items()},
            "present_in": self.present_in,
            "missing_from": self.missing_from,
            "is_consistent": self.is_consistent,
        }


@dataclass
class ResolveReport:
    paths: List[ResolvedPath] = field(default_factory=list)

    @property
    def inconsistent_paths(self) -> List[ResolvedPath]:
        return [p for p in self.paths if not p.is_consistent]

    @property
    def missing_paths(self) -> List[ResolvedPath]:
        return [p for p in self.paths if p.missing_from]

    def to_dict(self) -> dict:
        return {
            "total": len(self.paths),
            "inconsistent": len(self.inconsistent_paths),
            "missing": len(self.missing_paths),
            "paths": [p.to_dict() for p in self.paths],
        }


def resolve_paths(
    clients: Dict[str, VaultClient],
    paths: List[str],
) -> ResolveReport:
    """Read each path from every client and build a unified ResolveReport."""
    report = ResolveReport()
    for path in paths:
        resolved = ResolvedPath(path=path)
        for env, client in clients.items():
            try:
                data = client.read_secret(path)
            except Exception:
                data = None
            resolved.envs[env] = data
        report.paths.append(resolved)
    return report
