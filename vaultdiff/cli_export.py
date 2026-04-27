"""CLI sub-command: vaultdiff export — run a diff and write results to a file."""

from __future__ import annotations

import sys

import click

from vaultdiff.exporter import write_export
from vaultdiff.vault_client import VaultClient, VaultClientError
from vaultdiff.differ import VaultDiffer
from vaultdiff.filter import FilterConfig


@click.command("export")
@click.option("--left-addr", required=True, envvar="VAULT_LEFT_ADDR", help="Left Vault address.")
@click.option("--right-addr", required=True, envvar="VAULT_RIGHT_ADDR", help="Right Vault address.")
@click.option("--left-token", required=True, envvar="VAULT_LEFT_TOKEN", help="Left Vault token.")
@click.option("--right-token", required=True, envvar="VAULT_RIGHT_TOKEN", help="Right Vault token.")
@click.option("--path", "paths", multiple=True, required=True, help="Secret path(s) to compare.")
@click.option(
    "--format",
    "fmt",
    type=click.Choice(["json", "csv"], case_sensitive=False),
    default="json",
    show_default=True,
    help="Output file format.",
)
@click.option("--output", "-o", required=True, help="Destination file path.")
@click.option("--include-key", multiple=True, help="Key glob patterns to include.")
@click.option("--exclude-key", multiple=True, help="Key glob patterns to exclude.")
def export_command(
    left_addr,
    right_addr,
    left_token,
    right_token,
    paths,
    fmt,
    output,
    include_key,
    exclude_key,
):
    """Compare secret paths and export the diff to a file."""
    try:
        left_client = VaultClient(addr=left_addr, token=left_token)
        right_client = VaultClient(addr=right_addr, token=right_token)
    except VaultClientError as exc:
        click.echo(f"Vault connection error: {exc}", err=True)
        sys.exit(2)

    filter_cfg = FilterConfig(
        include_keys=list(include_key),
        exclude_keys=list(exclude_key),
    )
    differ = VaultDiffer(left=left_client, right=right_client, filter_config=filter_cfg)

    diffs = []
    for path in paths:
        try:
            diff = differ.diff_secret(path)
            diffs.append(diff)
        except VaultClientError as exc:
            click.echo(f"Error reading {path!r}: {exc}", err=True)
            sys.exit(2)

    try:
        write_export(diffs, fmt.lower(), output)
    except OSError as exc:
        click.echo(f"Failed to write output file: {exc}", err=True)
        sys.exit(2)

    click.echo(f"Exported {len(diffs)} diff(s) to {output!r} ({fmt}).")
