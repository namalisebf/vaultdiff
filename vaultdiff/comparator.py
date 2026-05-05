"""Path-level comparison report: aggregates per-path diffs into a structured
Comparison object that can be queried for overall pass/fail status."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from vaultdiff.differ import SecretDiff, VaultDiffer
from vaultdiff.filter import FilterConfig


@dataclass
class ComparisonResult:
    """Holds the outcome of comparing a set of paths between two Vault instances."""

    paths: List[str]
    diffs: Dict[str, SecretDiff] = field(default_factory=dict)
    errors: Dict[str, str] = field(default_factory=dict)

    # ------------------------------------------------------------------ #
    @property
    def passed(self) -> bool:
        """True when every compared path has no differences and no errors."""
        return not self.has_differences and not self.errors

    @property
    def has_differences(self) -> bool:
        return any(d.has_differences() for d in self.diffs.values())

    @property
    def changed_paths(self) -> List[str]:
        return [p for p, d in self.diffs.items() if d.has_differences()]

    @property
    def clean_paths(self) -> List[str]:
        return [p for p, d in self.diffs.items() if not d.has_differences()]

    def to_dict(self) -> dict:
        return {
            "passed": self.passed,
            "total_paths": len(self.paths),
            "changed_paths": self.changed_paths,
            "clean_paths": self.clean_paths,
            "error_paths": list(self.errors.keys()),
            "errors": self.errors,
        }


class Comparator:
    """Runs a multi-path comparison using a VaultDiffer and collects results."""

    def __init__(
        self,
        differ: VaultDiffer,
        filter_config: Optional[FilterConfig] = None,
    ) -> None:
        self._differ = differ
        self._filter = filter_config

    def compare(self, paths: List[str]) -> ComparisonResult:
        result = ComparisonResult(paths=list(paths))
        for path in paths:
            try:
                diff = self._differ.diff_secret(path, filter_config=self._filter)
                result.diffs[path] = diff
            except Exception as exc:  # noqa: BLE001
                result.errors[path] = str(exc)
        return result

    def compare_recursive(self, root: str) -> ComparisonResult:
        """Discover paths under *root* and compare them all."""
        try:
            paths = self._differ.diff_paths(root, filter_config=self._filter)
        except Exception as exc:  # noqa: BLE001
            result = ComparisonResult(paths=[])
            result.errors[root] = str(exc)
            return result
        discovered = [p for p in paths]
        return self.compare(discovered)
