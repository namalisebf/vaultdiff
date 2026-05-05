"""CLI command: vaultdiff rank — list paths ranked by change severity."""
from __future__ import annotations

import json
import sys
from typing import List

import click

from vaultdiff.vault_client import VaultClient, VaultClientError
from vaultdiff.differ import VaultDiffer
from vaultdiff.ranker import rank_diffs
from vaultdiff.formatter import OutputFormat


@click.command("rank")
@click.option("--left-addr", required=True, envvar="VAULT_LEFT_ADDR", help="Left Vault address.")
@click.option("--left-token", required=True, envvar="VAULT_LEFT_TOKEN", help="Left Vault token.")
@click.option("--right-addr", required=True, envvar="VAULT_RIGHT_ADDR", help="Right Vault address.")
@click.option("--right-token", required=True, envvar="VAULT_RIGHT_TOKEN", help="Right Vault token.")
@click.option("--path", "paths", multiple=True, required=True, help="Secret path(s) to compare.")
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["text", "json"], case_sensitive=False),
    default="text",
    show_default=True,
)
@click.option("--top", default=0, help="Show only top N results (0 = all).")
def rank_command(
    left_addr: str,
    left_token: str,
    right_addr: str,
    right_token: str,
    paths: List[str],
    output_format: str,
    top: int,
) -> None:
    """Rank secret paths by change severity (highest risk first)."""
    try:
        left = VaultClient(addr=left_addr, token=left_token)
        right = VaultClient(addr=right_addr, token=right_token)
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

    ranked = rank_diffs(diffs)
    if top > 0:
        ranked = ranked[:top]

    if output_format == "json":
        click.echo(json.dumps([r.to_dict() for r in ranked], indent=2))
    else:
        if not ranked:
            click.echo("No paths to rank.")
            return
        click.echo(f"{'PATH':<45} {'TIER':<10} {'SCORE':>8}")
        click.echo("-" * 65)
        for r in ranked:
            click.echo(f"{r.path:<45} {r.tier:<10} {r.weighted_score:>8.1f}")
