"""CLI command for drift detection against a saved snapshot."""

from __future__ import annotations

import json
import sys

import click

from vaultdiff.drift import detect_drift
from vaultdiff.snapshot import load_snapshot
from vaultdiff.vault_client import VaultClient, VaultClientError
from vaultdiff.differ import VaultDiffer


@click.command("drift")
@click.argument("snapshot_file", type=click.Path(exists=True))
@click.option("--vault-addr", envvar="VAULT_ADDR", required=True, help="Vault address for live comparison.")
@click.option("--vault-token", envvar="VAULT_TOKEN", required=True, help="Vault token.")
@click.option("--mount", default="secret", show_default=True, help="KV mount path.")
@click.option("--output", type=click.Choice(["text", "json"]), default="text", show_default=True)
@click.option("--exit-code", is_flag=True, default=False, help="Exit 1 if drift is detected.")
def drift_command(
    snapshot_file: str,
    vault_addr: str,
    vault_token: str,
    mount: str,
    output: str,
    exit_code: bool,
) -> None:
    """Detect drift between a snapshot file and the live Vault instance."""
    try:
        snapshot = load_snapshot(snapshot_file)
    except FileNotFoundError:
        click.echo(f"Snapshot file not found: {snapshot_file}", err=True)
        sys.exit(2)

    try:
        live_client = VaultClient(url=vault_addr, token=vault_token)
    except VaultClientError as exc:
        click.echo(f"Vault connection error: {exc}", err=True)
        sys.exit(2)

    differ = VaultDiffer(left_client=live_client, right_client=live_client)
    entries = detect_drift(snapshot=snapshot, differ=differ, mount=mount)

    drifted = [e for e in entries if e.has_drift]

    if output == "json":
        click.echo(json.dumps([e.to_dict() for e in entries], indent=2))
    else:
        if not drifted:
            click.echo("No drift detected.")
        for entry in drifted:
            click.echo(f"[DRIFT] {entry.path}")
            for k in entry.added_keys:
                click.echo(f"  + {k}")
            for k in entry.removed_keys:
                click.echo(f"  - {k}")
            for k in entry.changed_keys:
                click.echo(f"  ~ {k}")

    if exit_code and drifted:
        sys.exit(1)
