"""CLI command for batching vault diff results."""
from __future__ import annotations

import json
import sys

import click

from vaultdiff.batcher import BatchConfig, batch_diffs
from vaultdiff.differ import VaultDiffer
from vaultdiff.vault_client import VaultClient, VaultClientError


@click.command("batch")
@click.option("--left-addr", required=True, envvar="VAULT_LEFT_ADDR")
@click.option("--left-token", required=True, envvar="VAULT_LEFT_TOKEN")
@click.option("--right-addr", required=True, envvar="VAULT_RIGHT_ADDR")
@click.option("--right-token", required=True, envvar="VAULT_RIGHT_TOKEN")
@click.argument("paths", nargs=-1, required=True)
@click.option("--size", default=10, show_default=True, help="Items per batch.")
@click.option(
    "--skip-clean",
    is_flag=True,
    default=False,
    help="Exclude paths with no differences.",
)
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["text", "json"]),
    default="text",
    show_default=True,
)
def batch_command(
    left_addr: str,
    left_token: str,
    right_addr: str,
    right_token: str,
    paths: tuple,
    size: int,
    skip_clean: bool,
    output_format: str,
) -> None:
    """Batch vault diff results into fixed-size chunks."""
    try:
        left = VaultClient(left_addr, left_token)
        right = VaultClient(right_addr, right_token)
    except VaultClientError as exc:
        click.echo(f"Error: {exc}", err=True)
        sys.exit(1)

    differ = VaultDiffer(left, right)
    diffs = [differ.diff_secret(p) for p in paths]

    cfg = BatchConfig(size=size, skip_clean=skip_clean)
    report = batch_diffs(diffs, cfg)

    if output_format == "json":
        click.echo(json.dumps(report.to_dict(), indent=2))
    else:
        click.echo(f"Batches: {report.total_batches}  Paths: {report.total_paths}")
        for batch in report.batches:
            click.echo(
                f"  Batch {batch.index}: {batch.total} paths, "
                f"{batch.dirty_count} with differences"
            )
            for path in [item.path for item in batch.items]:
                click.echo(f"    - {path}")
