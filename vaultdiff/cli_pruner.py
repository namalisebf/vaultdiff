"""CLI command: vaultdiff prune — filter and prune diff results."""
from __future__ import annotations

import json
import sys
from typing import List

import click

from vaultdiff.cli import _build_clients
from vaultdiff.differ import VaultDiffer
from vaultdiff.formatter import OutputFormat
from vaultdiff.pruner import PruneConfig, prune_diffs
from vaultdiff.vault_client import VaultClientError


@click.command("prune")
@click.option("--left-addr", envvar="VAULT_LEFT_ADDR", required=True)
@click.option("--left-token", envvar="VAULT_LEFT_TOKEN", required=True)
@click.option("--right-addr", envvar="VAULT_RIGHT_ADDR", required=True)
@click.option("--right-token", envvar="VAULT_RIGHT_TOKEN", required=True)
@click.option("--path", "paths", multiple=True, required=True)
@click.option("--drop-clean", is_flag=True, default=False, help="Drop paths with no differences.")
@click.option("--exclude", "exclude_patterns", multiple=True, metavar="GLOB", help="Exclude paths matching glob.")
@click.option("--max-paths", type=int, default=None, help="Keep at most N paths.")
@click.option("--format", "fmt", type=click.Choice(["text", "json"]), default="text")
@click.pass_context
def prune_command(
    ctx: click.Context,
    left_addr: str,
    left_token: str,
    right_addr: str,
    right_token: str,
    paths: List[str],
    drop_clean: bool,
    exclude_patterns: List[str],
    max_paths,
    fmt: str,
) -> None:
    """Prune diff results by dropping clean or excluded paths."""
    try:
        left_client, right_client = _build_clients(
            left_addr, left_token, right_addr, right_token
        )
    except VaultClientError as exc:
        click.echo(f"Vault error: {exc}", err=True)
        sys.exit(1)

    differ = VaultDiffer(left_client, right_client)
    diffs = [differ.diff_secret(p) for p in paths]

    config = PruneConfig(
        drop_clean=drop_clean,
        exclude_patterns=list(exclude_patterns),
        max_paths=max_paths,
    )
    report = prune_diffs(diffs, config)

    if fmt == "json":
        click.echo(json.dumps(report.to_dict(), indent=2))
    else:
        click.echo(f"Kept {len(report.kept)} path(s), dropped {report.total_dropped}.")
        for diff in report.kept:
            marker = "*" if diff.has_differences else "-"
            click.echo(f"  [{marker}] {diff.path}")
        if report.dropped:
            click.echo("Dropped:")
            for diff in report.dropped:
                click.echo(f"  {diff.path}")
