"""CLI command for cataloging vault secret paths."""
from __future__ import annotations

import json
import sys

import click

from vaultdiff.vault_client import VaultClient, VaultClientError
from vaultdiff.differ import VaultDiffer
from vaultdiff.cataloger import catalog_diffs


@click.command("catalog")
@click.option("--left-addr", required=True, envvar="VAULT_LEFT_ADDR")
@click.option("--left-token", required=True, envvar="VAULT_LEFT_TOKEN")
@click.option("--right-addr", required=True, envvar="VAULT_RIGHT_ADDR")
@click.option("--right-token", required=True, envvar="VAULT_RIGHT_TOKEN")
@click.option("--path", "paths", multiple=True, required=True)
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["text", "json"]),
    default="text",
    show_default=True,
)
def catalog_command(
    left_addr, left_token, right_addr, right_token, paths, output_format
):
    """Catalog secret paths and display inventory metadata."""
    try:
        left = VaultClient(left_addr, left_token)
        right = VaultClient(right_addr, right_token)
    except VaultClientError as exc:
        click.echo(f"Error: {exc}", err=True)
        sys.exit(1)

    differ = VaultDiffer(left, right)
    diffs = []
    for path in paths:
        try:
            diffs.append(differ.diff_secret(path))
        except VaultClientError as exc:
            click.echo(f"Error reading {path}: {exc}", err=True)
            sys.exit(1)

    report = catalog_diffs(diffs)

    if output_format == "json":
        click.echo(json.dumps(report.to_dict(), indent=2))
        return

    click.echo(f"Catalog: {report.total_paths} path(s), {report.dirty_paths} with differences")
    for entry in report.entries:
        status = "DIRTY" if entry.has_differences else "CLEAN"
        tags_str = f" [{', '.join(entry.tags)}]" if entry.tags else ""
        click.echo(
            f"  [{status}] {entry.path}{tags_str} "
            f"keys={entry.total_keys} "
            f"changed={entry.changed_keys} "
            f"left_only={entry.only_in_left} "
            f"right_only={entry.only_in_right}"
        )
