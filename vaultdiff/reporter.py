"""High-level reporter that ties together the differ and formatters."""

import json
import sys
from typing import List, Optional, TextIO

from vaultdiff.differ import VaultDiffer
from vaultdiff.formatter import OutputFormat, format_diff_json, format_diff_text
from vaultdiff.vault_client import VaultClient


class Reporter:
    """Orchestrates diffing one or more paths and writing formatted output."""

    def __init__(
        self,
        left_client: VaultClient,
        right_client: VaultClient,
        output_format: str = OutputFormat.TEXT,
        color: bool = True,
        out: Optional[TextIO] = None,
    ) -> None:
        self._differ = VaultDiffer(left_client, right_client)
        self._format = output_format
        self._color = color
        self._out = out or sys.stdout

    def report_path(self, path: str) -> bool:
        """Diff *path* and write results. Returns True if differences found."""
        diffs = self._differ.diff_secret(path)

        if self._format == OutputFormat.JSON:
            payload = format_diff_json(path, diffs)
            self._out.write(json.dumps(payload, indent=2))
            self._out.write("\n")
        else:
            text = format_diff_text(path, diffs, color=self._color)
            self._out.write(text)
            self._out.write("\n")

        return bool(diffs)

    def report_paths(self, paths: List[str]) -> bool:
        """Diff multiple paths. Returns True if *any* path has differences."""
        found_any = False
        for path in paths:
            if self.report_path(path):
                found_any = True
        return found_any

    def report_recursive(self, base_path: str) -> bool:
        """List and diff all secrets under *base_path* recursively."""
        paths = self._differ.diff_paths(base_path)
        all_paths = [p for p in paths if not p.endswith("/")]
        return self.report_paths(all_paths)
