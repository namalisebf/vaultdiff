"""Export diff results to various file formats (JSON, CSV)."""

from __future__ import annotations

import csv
import io
import json
from typing import List

from vaultdiff.differ import SecretDiff


def export_diffs_json(diffs: List[SecretDiff], indent: int = 2) -> str:
    """Serialize a list of SecretDiff objects to a JSON string."""
    records = []
    for diff in diffs:
        records.append(
            {
                "path": diff.path,
                "changed": [
                    {"key": k, "left": lv, "right": rv}
                    for k, (lv, rv) in diff.changed.items()
                ],
                "only_in_left": [
                    {"key": k, "value": v} for k, v in diff.only_in_left.items()
                ],
                "only_in_right": [
                    {"key": k, "value": v} for k, v in diff.only_in_right.items()
                ],
            }
        )
    return json.dumps(records, indent=indent)


def export_diffs_csv(diffs: List[SecretDiff]) -> str:
    """Serialize a list of SecretDiff objects to a CSV string.

    Columns: path, change_type, key, left_value, right_value
    """
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["path", "change_type", "key", "left_value", "right_value"])

    for diff in diffs:
        for key, (left_val, right_val) in diff.changed.items():
            writer.writerow([diff.path, "changed", key, left_val, right_val])
        for key, value in diff.only_in_left.items():
            writer.writerow([diff.path, "removed", key, value, ""])
        for key, value in diff.only_in_right.items():
            writer.writerow([diff.path, "added", key, "", value])

    return output.getvalue()


def write_export(diffs: List[SecretDiff], fmt: str, filepath: str) -> None:
    """Write exported diffs to *filepath* in the requested format.

    Args:
        diffs: list of SecretDiff results.
        fmt: ``'json'`` or ``'csv'``.
        filepath: destination file path.

    Raises:
        ValueError: if *fmt* is not supported.
    """
    if fmt == "json":
        content = export_diffs_json(diffs)
    elif fmt == "csv":
        content = export_diffs_csv(diffs)
    else:
        raise ValueError(f"Unsupported export format: {fmt!r}. Choose 'json' or 'csv'.")

    with open(filepath, "w", encoding="utf-8") as fh:
        fh.write(content)
