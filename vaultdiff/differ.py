"""Diff engine for comparing Vault secret paths."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from vaultdiff.vault_client import VaultClient
from vaultdiff.filter import FilterConfig, DEFAULT_FILTER


@dataclass
class SecretDiff:
    path: str
    changed: Dict[str, tuple] = field(default_factory=dict)   # key -> (left, right)
    only_in_left: Dict[str, str] = field(default_factory=dict)
    only_in_right: Dict[str, str] = field(default_factory=dict)

    @property
    def has_differences(self) -> bool:
        return bool(self.changed or self.only_in_left or self.only_in_right)


# Kept for backward compatibility
def has_differences(diff: SecretDiff) -> bool:
    return diff.has_differences


class VaultDiffer:
    def __init__(
        self,
        left_client: VaultClient,
        right_client: VaultClient,
        filter_config: Optional[FilterConfig] = None,
    ) -> None:
        self.left = left_client
        self.right = right_client
        self.filter = filter_config or DEFAULT_FILTER

    def diff_secret(self, path: str) -> SecretDiff:
        """Compare a single secret path between left and right Vault."""
        left_data = self.left.read_secret(path) or {}
        right_data = self.right.read_secret(path) or {}

        all_keys = self.filter.filter_keys(
            set(left_data.keys()) | set(right_data.keys())
        )

        diff = SecretDiff(path=path)
        for key in all_keys:
            in_left = key in left_data
            in_right = key in right_data
            if in_left and in_right:
                if left_data[key] != right_data[key]:
                    diff.changed[key] = (left_data[key], right_data[key])
            elif in_left:
                diff.only_in_left[key] = left_data[key]
            else:
                diff.only_in_right[key] = right_data[key]
        return diff

    def diff_paths(self, paths: List[str]) -> List[SecretDiff]:
        """Compare multiple secret paths, respecting path filter rules."""
        allowed = self.filter.filter_paths(paths)
        return [self.diff_secret(p) for p in allowed]

    def diff_recursive(self, mount: str) -> List[SecretDiff]:
        """Recursively diff all secrets under *mount* using the left client."""
        paths = self.left.list_secrets(mount)
        return self.diff_paths(paths)
