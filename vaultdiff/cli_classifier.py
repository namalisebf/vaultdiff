"""CLI command: classify secret paths by sensitivity tier."""
from __future__ import annotations

import json
import sys
from typing import List, Optional

import click

from vaultdiff.classifier import ClassifierConfig, classify_diffs
from vaultdiff.differ import VaultDiffer
from vaultdiff.vault_client import VaultClient, VaultClientError


@click.command("classify")
@click.option("--left-addr", required=True, envvar="VAULT_LEFT_ADDR")
@click.option("--left-token", required=True, envvar="VAULT_LEFT_TOKEN")
@click.option("--right-addr", required=True, envvar="VAULT_RIGHT_ADDR")
@click.option("--right-token", required=True, envvar="VAULT_RIGHT_TOKEN")
@click.argument("paths", nargs=-1, required=True)
@click.option("--format", "output_format", default="text", type=click.Choice(["text", "json"]))
@click.option("--min-tier", default="low", type=click.Choice(["critical", "high", "medium", "low"]))
@click.pass_context
def classify_command(
    ctx: click.Context,
    left_addr: str,
    left_token: str,
    right_addr: str,
    right_token: str,
    paths: List[str],
    output_format: str,
    min_tier: str,
) -> None:
    """Classify secret paths by sensitivity tier."""
    from vaultdiff.classifier import SENSITIVITY_TIERS

    try:
        left_client = VaultClient(url=left_addr, token=left_token)
        right_client = VaultClient(url=right_addr, token=right_token)
    except VaultClientError as exc:
        click.echo(f"Vault error: {exc}", err=True)
        sys.exit(1)

    differ = VaultDiffer(left=left_client, right=right_client)
    config = ClassifierConfig()
    tier_index = SENSITIVITY_TIERS.index(min_tier)

    try:
        diffs = [differ.diff_secret(p) for p in paths]
    except VaultClientError as exc:
        click.echo(f"Vault error: {exc}", err=True)
        sys.exit(1)

    classified = [
        c for c in classify_diffs(diffs, config)
        if SENSITIVITY_TIERS.index(c.tier) <= tier_index
    ]

    if output_format == "json":
        click.echo(json.dumps([c.to_dict() for c in classified], indent=2))
    else:
        if not classified:
            click.echo("No paths matched the specified tier threshold.")
            return
        for item in classified:
            click.echo(f"[{item.tier.upper():8s}] {item.path}")
            for key in item.matched_keys:
                click.echo(f"           - {key}")
