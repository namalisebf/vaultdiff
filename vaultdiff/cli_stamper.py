"""CLI command: stamp — attach timestamps to diff results."""
from __future__ import annotations

import json
import sys

import click

from vaultdiff.vault_client import VaultClient, VaultClientError
from vaultdiff.differ import VaultDiffer
from vaultdiff.stamper import stamp_diffs


@click.command("stamp")
@click.option("--left-addr", required=True, envvar="VAULT_LEFT_ADDR")
@click.option("--left-token", required=True, envvar="VAULT_LEFT_TOKEN")
@click.option("--right-addr", required=True, envvar="VAULT_RIGHT_ADDR")
@click.option("--right-token", required=True, envvar="VAULT_RIGHT_TOKEN")
@click.option("--path", "paths", multiple=True, required=True)
@click.option("--label", default=None, help="Optional label attached to each stamped entry.")
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["text", "json"]),
    default="text",
)
@click.option("--exit-code", is_flag=True, default=False)
def stamp_command(
    left_addr, left_token, right_addr, right_token, paths, label, output_format, exit_code
):
    """Stamp diff results with a timestamp and optional label."""
    try:
        left = VaultClient(addr=left_addr, token=left_token)
        right = VaultClient(addr=right_addr, token=right_token)
    except VaultClientError as exc:
        click.echo(f"Error: {exc}", err=True)
        sys.exit(1)

    differ = VaultDiffer(left=left, right=right)
    diffs = []
    for path in paths:
        try:
            diffs.append(differ.diff_secret(path))
        except VaultClientError as exc:
            click.echo(f"Error reading {path}: {exc}", err=True)
            sys.exit(1)

    report = stamp_diffs(diffs, label=label)

    if output_format == "json":
        click.echo(json.dumps(report.to_dict(), indent=2))
    else:
        for entry in report.entries:
            status = "DIRTY" if entry.has_differences() else "CLEAN"
            lbl = f" [{entry.label}]" if entry.label else ""
        click.echo(
                f"{entry.path}: {status}{lbl} @ {entry.stamped_at.isoformat()}"
            )

    if exit_code and report.dirty_paths > 0:
        sys.exit(1)
