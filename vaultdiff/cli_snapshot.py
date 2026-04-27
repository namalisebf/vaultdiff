"""CLI commands for snapshot capture and comparison."""

from __future__ import annotations

import json
import sys

import click

from vaultdiff.reporter import Reporter
from vaultdiff.snapshot import SnapshotEntry, Snapshot, save_snapshot, load_snapshot, diff_snapshots
from vaultdiff.vault_client import VaultClient, VaultClientError


@click.group("snapshot")
def snapshot_command() -> None:
    """Capture and compare Vault secret path snapshots."""


@snapshot_command.command("capture")
@click.option("--url", envvar="VAULT_ADDR", required=True, help="Vault address.")
@click.option("--token", envvar="VAULT_TOKEN", required=True, help="Vault token.")
@click.option("--path", "root_path", required=True, help="Root path to snapshot recursively.")
@click.option("--label", required=True, help="Human-readable label for this snapshot.")
@click.option("--output", required=True, help="File path to write snapshot JSON.")
def capture_command(url: str, token: str, root_path: str, label: str, output: str) -> None:
    """Capture a snapshot of all secret key names under a Vault path."""
    try:
        client = VaultClient(url=url, token=token)
    except VaultClientError as exc:
        click.echo(f"Vault error: {exc}", err=True)
        sys.exit(1)

    reporter = Reporter(client)
    entries = []

    try:
        paths = reporter._collect_paths(root_path)
    except VaultClientError as exc:
        click.echo(f"Vault error: {exc}", err=True)
        sys.exit(1)

    for p in paths:
        try:
            secret = client.read_secret(p)
            keys = list(secret.keys()) if secret else []
        except VaultClientError:
            keys = []
        entries.append(SnapshotEntry(path=p, keys=keys))

    snapshot = Snapshot(label=label, entries=entries)
    save_snapshot(snapshot, output)
    click.echo(f"Snapshot '{label}' saved to {output} ({len(entries)} paths).")


@snapshot_command.command("compare")
@click.argument("old_file")
@click.argument("new_file")
@click.option("--format", "fmt", default="text", type=click.Choice(["text", "json"]), help="Output format.")
def compare_command(old_file: str, new_file: str, fmt: str) -> None:
    """Compare two snapshot files and report structural differences."""
    try:
        old_snap = load_snapshot(old_file)
        new_snap = load_snapshot(new_file)
    except FileNotFoundError as exc:
        click.echo(str(exc), err=True)
        sys.exit(1)

    changes = diff_snapshots(old_snap, new_snap)

    if fmt == "json":
        click.echo(json.dumps({"old": old_snap.label, "new": new_snap.label, "changes": changes}, indent=2))
    else:
        if not changes:
            click.echo("No structural differences found between snapshots.")
        else:
            click.echo(f"Comparing '{old_snap.label}' -> '{new_snap.label}':\n")
            for path, info in changes.items():
                click.echo(f"  [{info['status'].upper()}] {path}")
                for k in info.get("keys_added", []):
                    click.echo(f"    + {k}")
                for k in info.get("keys_removed", []):
                    click.echo(f"    - {k}")

    if changes:
        sys.exit(1)
