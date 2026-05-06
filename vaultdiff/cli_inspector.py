"""CLI command: vaultdiff inspect — show per-key metadata for secret paths."""
from __future__ import annotations

import json
import sys

import click

from vaultdiff.vault_client import VaultClient, VaultClientError
from vaultdiff.differ import VaultDiffer
from vaultdiff.inspector import inspect_diffs


@click.command("inspect")
@click.option("--left-addr", required=True, envvar="VAULT_LEFT_ADDR", help="Left Vault address.")
@click.option("--left-token", required=True, envvar="VAULT_LEFT_TOKEN", help="Left Vault token.")
@click.option("--right-addr", required=True, envvar="VAULT_RIGHT_ADDR", help="Right Vault address.")
@click.option("--right-token", required=True, envvar="VAULT_RIGHT_TOKEN", help="Right Vault token.")
@click.option("--path", "paths", multiple=True, required=True, help="Secret path(s) to inspect.")
@click.option("--format", "fmt", default="text", type=click.Choice(["text", "json"]), show_default=True)
@click.option("--only-changed", is_flag=True, default=False, help="Only show keys that differ.")
def inspect_command(
    left_addr: str,
    left_token: str,
    right_addr: str,
    right_token: str,
    paths: tuple,
    fmt: str,
    only_changed: bool,
) -> None:
    """Inspect per-key metadata (type, length, entropy) across environments."""
    try:
        left_client = VaultClient(url=left_addr, token=left_token)
        right_client = VaultClient(url=right_addr, token=right_token)
    except VaultClientError as exc:
        click.echo(f"Vault client error: {exc}", err=True)
        sys.exit(1)

    differ = VaultDiffer(left=left_client, right=right_client)

    try:
        diffs = [differ.diff_secret(p) for p in paths]
    except VaultClientError as exc:
        click.echo(f"Error reading secrets: {exc}", err=True)
        sys.exit(1)

    if only_changed:
        diffs = [d for d in diffs if d.has_differences()]

    inspections = inspect_diffs(diffs)

    if fmt == "json":
        click.echo(json.dumps([i.to_dict() for i in inspections], indent=2))
        return

    for insp in inspections:
        click.echo(f"\nPath: {insp.path}")
        if not insp.keys:
            click.echo("  (no differing keys)")
            continue
        header = f"  {'KEY':<30} {'L-LEN':>6} {'R-LEN':>6} {'L-ENT':>7} {'R-ENT':>7}  {'L-TYPE':<18} {'R-TYPE':<18}"
        click.echo(header)
        click.echo("  " + "-" * (len(header) - 2))
        for ki in insp.keys:
            ll = str(ki.left_length) if ki.left_length is not None else "-"
            rl = str(ki.right_length) if ki.right_length is not None else "-"
            le = f"{ki.left_entropy:.3f}" if ki.left_entropy is not None else "-"
            re = f"{ki.right_entropy:.3f}" if ki.right_entropy is not None else "-"
            lt = ki.left_type or "-"
            rt = ki.right_type or "-"
            click.echo(f"  {ki.key:<30} {ll:>6} {rl:>6} {le:>7} {re:>7}  {lt:<18} {rt:<18}")
