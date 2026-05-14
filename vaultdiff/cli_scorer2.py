"""CLI command: weighted-score."""
from __future__ import annotations

import json
import sys

import click

from vaultdiff.vault_client import VaultClient, VaultClientError
from vaultdiff.differ import VaultDiffer
from vaultdiff.scorer2 import WeightedScoreConfig, score_diffs_weighted


@click.command("weighted-score")
@click.option("--left-addr", required=True, envvar="VAULT_LEFT_ADDR")
@click.option("--left-token", required=True, envvar="VAULT_LEFT_TOKEN")
@click.option("--right-addr", required=True, envvar="VAULT_RIGHT_ADDR")
@click.option("--right-token", required=True, envvar="VAULT_RIGHT_TOKEN")
@click.option("--path", "paths", multiple=True, required=True)
@click.option("--weight-changed", default=3.0, show_default=True, type=float)
@click.option("--weight-left", default=1.0, show_default=True, type=float)
@click.option("--weight-right", default=1.0, show_default=True, type=float)
@click.option("--format", "fmt", default="text", type=click.Choice(["text", "json"]))
@click.option("--top", default=0, type=int, help="Show only top N results (0 = all)")
@click.pass_context
def weighted_score_command(
    ctx: click.Context,
    left_addr: str,
    left_token: str,
    right_addr: str,
    right_token: str,
    paths: tuple,
    weight_changed: float,
    weight_left: float,
    weight_right: float,
    fmt: str,
    top: int,
) -> None:
    """Score secret paths by weighted change magnitude."""
    try:
        left = VaultClient(left_addr, left_token)
        right = VaultClient(right_addr, right_token)
    except VaultClientError as exc:
        click.echo(f"Error: {exc}", err=True)
        sys.exit(1)

    differ = VaultDiffer(left, right)
    diffs = [differ.diff_secret(p) for p in paths]

    config = WeightedScoreConfig(
        weights={
            "changed": weight_changed,
            "only_in_left": weight_left,
            "only_in_right": weight_right,
        }
    )
    report = score_diffs_weighted(diffs, config)
    entries = report.entries[:top] if top > 0 else report.entries

    if fmt == "json":
        click.echo(json.dumps({"total_score": report.total_score, "entries": [e.to_dict() for e in entries]}, indent=2))
    else:
        if not entries:
            click.echo("No paths scored.")
            return
        for e in entries:
            click.echo(f"{e.path}  score={e.score:.1f}  changed={e.changed_keys}  left={e.only_in_left}  right={e.only_in_right}")
        click.echo(f"Total score: {report.total_score:.1f}")
