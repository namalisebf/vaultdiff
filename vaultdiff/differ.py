"""Module for comparing secrets between two Vault paths."""

from dataclasses import dataclass, field
from typing import Any

from vaultdiff.vault_client import VaultClient


@dataclass
class SecretDiff:
    """Represents the diff result between two Vault secret paths."""

    path: str
    only_in_left: dict[str, Any] = field(default_factory=dict)
    only_in_right: dict[str, Any] = field(default_factory=dict)
    changed: dict[str, tuple[Any, Any]] = field(default_factory=dict)
    unchanged: list[str] = field(default_factory=list)

    @property
    def has_differences(self) -> bool:
        return bool(self.only_in_left or self.only_in_right or self.changed)


class VaultDiffer:
    """Compares secrets between two Vault clients at a given path."""

    def __init__(self, left: VaultClient, right: VaultClient) -> None:
        self.left = left
        self.right = right

    def diff_secret(self, path: str) -> SecretDiff:
        """Compare a single secret path between left and right Vault instances."""
        left_data = self.left.read_secret(path) or {}
        right_data = self.right.read_secret(path) or {}

        diff = SecretDiff(path=path)

        all_keys = set(left_data) | set(right_data)

        for key in all_keys:
            in_left = key in left_data
            in_right = key in right_data

            if in_left and not in_right:
                diff.only_in_left[key] = left_data[key]
            elif in_right and not in_left:
                diff.only_in_right[key] = right_data[key]
            elif left_data[key] != right_data[key]:
                diff.changed[key] = (left_data[key], right_data[key])
            else:
                diff.unchanged.append(key)

        return diff

    def diff_recursive(self, path: str) -> list[SecretDiff]:
        """Recursively compare all secrets under a given path."""
        results: list[SecretDiff] = []

        left_keys = set(self.left.list_secrets(path) or [])
        right_keys = set(self.right.list_secrets(path) or [])
        all_keys = left_keys | right_keys

        for key in sorted(all_keys):
            full_path = f"{path.rstrip('/')}/{key}"
            if key.endswith("/"):
                results.extend(self.diff_recursive(full_path.rstrip("/")))
            else:
                results.append(self.diff_secret(full_path))

        return results
