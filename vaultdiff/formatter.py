"""Output formatters for VaultDiff results."""

from typing import List
from vaultdiff.differ import SecretDiff


TERM_RED = "\033[31m"
TERM_GREEN = "\033[32m"
TERM_YELLOW = "\033[33m"
TERM_RESET = "\033[0m"


class OutputFormat:
    TEXT = "text"
    JSON = "json"


def format_diff_text(path: str, diffs: List[SecretDiff], color: bool = True) -> str:
    """Format a list of SecretDiff entries as a human-readable text block."""
    lines = [f"--- {path} (left)"]
    lines.append(f"+++ {path} (right)")

    if not diffs:
        marker = f"{TERM_GREEN}={TERM_RESET}" if color else "="
        lines.append(f"  {marker}  (no differences)")
        return "\n".join(lines)

    for diff in sorted(diffs, key=lambda d: d.key):
        if diff.only_in_left:
            prefix = f"{TERM_RED}-{TERM_RESET}" if color else "-"
            lines.append(f"  {prefix}  {diff.key}: {diff.left_value!r}")
        elif diff.only_in_right:
            prefix = f"{TERM_GREEN}+{TERM_RESET}" if color else "+"
            lines.append(f"  {prefix}  {diff.key}: {diff.right_value!r}")
        else:
            prefix = f"{TERM_YELLOW}~{TERM_RESET}" if color else "~"
            lines.append(
                f"  {prefix}  {diff.key}: {diff.left_value!r} -> {diff.right_value!r}"
            )

    return "\n".join(lines)


def format_diff_json(path: str, diffs: List[SecretDiff]) -> dict:
    """Format a list of SecretDiff entries as a serialisable dict."""
    entries = []
    for diff in sorted(diffs, key=lambda d: d.key):
        if diff.only_in_left:
            change_type = "removed"
        elif diff.only_in_right:
            change_type = "added"
        else:
            change_type = "changed"

        entries.append(
            {
                "key": diff.key,
                "change": change_type,
                "left": diff.left_value,
                "right": diff.right_value,
            }
        )

    return {"path": path, "differences": entries, "total": len(entries)}
