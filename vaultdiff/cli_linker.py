"""cli_linker.py — CLI command to report cross-path key linkage."""
from __future__ import annotations

import json
import sys

import click

from vaultdiff.vault_client import VaultClient, VaultClientError
from vaultdiff.differ import VaultDiffer
from vaultdiff.linker import build_link_report


@click.command("link")
@click.option("--left-addr", required=True, envvar="VAULT_LEFT_ADDR", help="Left Vault address.")
@click.option("--left-token", required=True, envvar="VAULT_LEFT_TOKEN", help="Left Vault token.")
@click.option("--right-addr", required=True, envvar="VAULT_RIGHT_ADDR", help="Right Vault address.")
@click.option("--right-token", required=True, envvar="VAULT_RIGHT_TOKEN", help="Right Vault token.")
@click.option("--path", "paths", multiple=True, required=True, help="Secret path(s) to compare.")
@click.option("--min-links", default=2, show_default=True, help="Minimum paths sharing a key to report it.")
@click.option("--format", "output_format", default="text", type=click.Choice(["text", "json"]), show_default=True)
@click.option("--exit-code", is_flag=True, default=False, help="Exit 1 when shared keys are found.")
def link_command(
    left_addr: str,
    left_token: str,
    right_addr: str,
    right_token: str,
    paths: tuple,
    min_links: int,
    output_format: str,
    exit_code: bool,
) -> None:
    """Report keys that are changed across multiple secret paths simultaneously."""
    try:
        left_client = VaultClient(vault_addr=left_addr, vault_token=left_token)
        right_client = VaultClient(vault_addr=right_addr, vault_token=right_token)
    except VaultClientError as exc:
        click.echo(f"Vault client error: {exc}", err=True)
        sys.exit(1)

    differ = VaultDiffer(left_client=left_client, right_client=right_client)

    diffs = []
    for path in paths:
        try:
            diffs.append(differ.diff_secret(path))
        except VaultClientError as exc:
            click.echo(f"Error reading '{path}': {exc}", err=True)
            sys.exit(1)

    report = build_link_report(diffs, min_links=min_links)

    if output_format == "json":
        click.echo(json.dumps(report.to_dict(), indent=2))
    else:
        if report.total_shared_keys == 0:
            click.echo("No shared changed keys found across the specified paths.")
        else:
            click.echo(
                f"Found {report.total_shared_keys} shared key(s) "
                f"across {report.total_affected_paths} path(s):"
            )
            for lk in report.linked_keys:
                paths_str = ", ".join(lk.paths)
                click.echo(f"  [{lk.link_count}]  {lk.key}  ->  {paths_str}")

    if exit_code and report.total_shared_keys > 0:
        sys.exit(1)
