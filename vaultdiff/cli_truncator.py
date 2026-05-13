"""CLI command: truncate — report diffs with per-path key limits."""
from __future__ import annotations

import json
import sys

import click

from vaultdiff.vault_client import VaultClient, VaultClientError
from vaultdiff.differ import VaultDiffer
from vaultdiff.truncator import TruncateConfig, truncate_diffs


@click.command("truncate")
@click.option("--left-addr", required=True, envvar="VAULT_LEFT_ADDR")
@click.option("--left-token", required=True, envvar="VAULT_LEFT_TOKEN")
@click.option("--right-addr", required=True, envvar="VAULT_RIGHT_ADDR")
@click.option("--right-token", required=True, envvar="VAULT_RIGHT_TOKEN")
@click.option("--path", "paths", multiple=True, required=True)
@click.option("--max-changed", type=int, default=None, help="Max changed keys per path.")
@click.option("--max-left", type=int, default=None, help="Max only-in-left keys per path.")
@click.option("--max-right", type=int, default=None, help="Max only-in-right keys per path.")
@click.option("--format", "fmt", type=click.Choice(["text", "json"]), default="text")
def truncate_command(
    left_addr, left_token, right_addr, right_token,
    paths, max_changed, max_left, max_right, fmt,
):
    """Diff secrets and truncate key lists to manageable sizes."""
    try:
        left_client = VaultClient(addr=left_addr, token=left_token)
        right_client = VaultClient(addr=right_addr, token=right_token)
    except VaultClientError as exc:
        click.echo(f"Error: {exc}", err=True)
        sys.exit(1)

    differ = VaultDiffer(left_client, right_client)
    config = TruncateConfig(
        max_changed_keys=max_changed,
        max_only_in_left=max_left,
        max_only_in_right=max_right,
    )

    try:
        diffs = [differ.diff_secret(p) for p in paths]
    except VaultClientError as exc:
        click.echo(f"Error: {exc}", err=True)
        sys.exit(1)

    report = truncate_diffs(diffs, config)

    if fmt == "json":
        click.echo(json.dumps(report.to_dict(), indent=2))
        return

    for entry in report.entries:
        click.echo(f"Path: {entry.path}")
        if entry.changed_keys:
            click.echo(f"  Changed ({len(entry.changed_keys)}): {', '.join(entry.changed_keys)}")
            if entry.truncated_changed:
                click.echo(f"    ... and {entry.truncated_changed} more (truncated)")
        if entry.only_in_left:
            click.echo(f"  Only in left ({len(entry.only_in_left)}): {', '.join(entry.only_in_left)}")
            if entry.truncated_left:
                click.echo(f"    ... and {entry.truncated_left} more (truncated)")
        if entry.only_in_right:
            click.echo(f"  Only in right ({len(entry.only_in_right)}): {', '.join(entry.only_in_right)}")
            if entry.truncated_right:
                click.echo(f"    ... and {entry.truncated_right} more (truncated)")
        if not entry.has_differences():
            click.echo("  No differences.")

    total = report.total_truncated()
    if total:
        click.echo(f"\nTotal keys truncated: {total}")
