"""CLI command: vaultdiff index — build and display a secret path index."""
from __future__ import annotations

import json
import sys

import click

from vaultdiff.cli import _build_vault_clients
from vaultdiff.differ import VaultDiffer
from vaultdiff.formatter import OutputFormat
from vaultdiff.indexer import build_index
from vaultdiff.vault_client import VaultClientError


@click.command("index")
@click.option("--left-addr", required=True, envvar="VAULT_LEFT_ADDR", help="Left Vault address.")
@click.option("--left-token", required=True, envvar="VAULT_LEFT_TOKEN", help="Left Vault token.")
@click.option("--right-addr", required=True, envvar="VAULT_RIGHT_ADDR", help="Right Vault address.")
@click.option("--right-token", required=True, envvar="VAULT_RIGHT_TOKEN", help="Right Vault token.")
@click.option("--path", "paths", multiple=True, required=True, help="Secret path(s) to index.")
@click.option("--side", default="left", show_default=True, type=click.Choice(["left", "right"]), help="Which side to fingerprint.")
@click.option("--format", "fmt", default="text", show_default=True, type=click.Choice(["text", "json"]), help="Output format.")
@click.option("--key", "filter_key", default=None, help="Show only entries containing this key.")
def index_command(
    left_addr: str,
    left_token: str,
    right_addr: str,
    right_token: str,
    paths: tuple,
    side: str,
    fmt: str,
    filter_key: str | None,
) -> None:
    """Build a key-presence and value-fingerprint index across secret paths."""
    try:
        left_client, right_client = _build_vault_clients(
            left_addr, left_token, right_addr, right_token
        )
    except VaultClientError as exc:
        click.echo(f"Vault error: {exc}", err=True)
        sys.exit(1)

    differ = VaultDiffer(left_client, right_client)
    diffs = []
    for path in paths:
        try:
            diffs.append(differ.diff_secret(path))
        except VaultClientError as exc:
            click.echo(f"Vault error reading {path!r}: {exc}", err=True)
            sys.exit(1)

    index = build_index(diffs, side=side)

    entries = (
        [e for e in index.entries if filter_key in e.keys]
        if filter_key
        else index.entries
    )

    if fmt == "json":
        click.echo(json.dumps({"entries": [e.to_dict() for e in entries]}, indent=2))
        return

    if not entries:
        click.echo("No indexed paths.")
        return

    for entry in entries:
        click.echo(f"path: {entry.path}")
        for key in entry.keys:
            fp = entry.fingerprints.get(key, "(no fingerprint)")
            click.echo(f"  {key}: {fp}")
