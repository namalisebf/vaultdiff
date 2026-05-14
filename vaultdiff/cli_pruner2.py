"""CLI command: prune2 — drop diffs below a score threshold."""
from __future__ import annotations

import json
import sys

import click

from vaultdiff.vault_client import VaultClient, VaultClientError
from vaultdiff.differ import VaultDiffer
from vaultdiff.pruner2 import ScorePruneConfig, score_prune


@click.command("prune2")
@click.option("--left-addr", required=True, envvar="VAULT_LEFT_ADDR")
@click.option("--left-token", required=True, envvar="VAULT_LEFT_TOKEN")
@click.option("--right-addr", required=True, envvar="VAULT_RIGHT_ADDR")
@click.option("--right-token", required=True, envvar="VAULT_RIGHT_TOKEN")
@click.option("--path", "paths", multiple=True, required=True)
@click.option("--min-score", default=0.0, type=float, show_default=True)
@click.option("--drop-clean", is_flag=True, default=False)
@click.option("--max-paths", default=None, type=int)
@click.option("--format", "fmt", type=click.Choice(["text", "json"]), default="text")
def prune2_command(
    left_addr, left_token, right_addr, right_token,
    paths, min_score, drop_clean, max_paths, fmt,
):
    """Prune diff results that fall below a minimum score."""
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

    config = ScorePruneConfig(
        min_score=min_score,
        drop_clean=drop_clean,
        max_paths=max_paths,
    )
    report = score_prune(diffs, config)

    if fmt == "json":
        click.echo(json.dumps(report.to_dict(), indent=2))
    else:
        click.echo(f"Kept:    {report.total_kept}")
        click.echo(f"Dropped: {report.total_dropped}")
        for diff in report.kept:
            status = "DIRTY" if diff.has_differences() else "clean"
            click.echo(f"  [{status}] {diff.path}")
