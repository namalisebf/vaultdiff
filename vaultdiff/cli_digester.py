"""CLI command: vaultdiff digest — show per-path digest comparison."""
from __future__ import annotations

import json
import sys

import click

from vaultdiff.vault_client import VaultClient, VaultClientError
from vaultdiff.differ import VaultDiffer
from vaultdiff.digester import digest_diffs
from vaultdiff.formatter import OutputFormat


@click.command("digest")
@click.option("--left-addr", required=True, envvar="VAULT_LEFT_ADDR")
@click.option("--left-token", required=True, envvar="VAULT_LEFT_TOKEN")
@click.option("--right-addr", required=True, envvar="VAULT_RIGHT_ADDR")
@click.option("--right-token", required=True, envvar="VAULT_RIGHT_TOKEN")
@click.option("--path", "paths", multiple=True, required=True)
@click.option("--format", "fmt", type=click.Choice(["text", "json"]), default="text")
@click.option("--exit-code", is_flag=True, default=False,
              help="Exit 1 if any digests mismatch.")
def digest_command(
    left_addr: str,
    left_token: str,
    right_addr: str,
    right_token: str,
    paths: tuple,
    fmt: str,
    exit_code: bool,
) -> None:
    """Compare SHA-256 digests of secrets between two Vault instances."""
    try:
        left_client = VaultClient(left_addr, left_token)
        right_client = VaultClient(right_addr, right_token)
    except VaultClientError as exc:
        click.echo(f"Vault connection error: {exc}", err=True)
        sys.exit(1)

    differ = VaultDiffer(left_client, right_client)

    try:
        diffs = [differ.diff_secret(p) for p in paths]
    except VaultClientError as exc:
        click.echo(f"Error reading secrets: {exc}", err=True)
        sys.exit(1)

    report = digest_diffs(diffs)

    if fmt == "json":
        click.echo(json.dumps(report.to_dict(), indent=2))
    else:
        for entry in report.entries:
            status = "MATCH" if entry.match else "MISMATCH"
            click.echo(f"{entry.path}: {status}")
            click.echo(f"  left : {entry.left_digest or 'N/A'}")
            click.echo(f"  right: {entry.right_digest or 'N/A'}")

    if exit_code and not report.all_match:
        sys.exit(1)
