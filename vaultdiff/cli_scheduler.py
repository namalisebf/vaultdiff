"""CLI command for running scheduled Vault diffs."""

from __future__ import annotations

import json
import sys
from typing import Optional

import click

from vaultdiff.differ import VaultDiffer
from vaultdiff.formatter import OutputFormat, format_diff_text
from vaultdiff.scheduler import ScheduleConfig, Scheduler
from vaultdiff.vault_client import VaultClient, VaultClientError


@click.command("schedule")
@click.option("--left-addr", required=True, envvar="VAULT_LEFT_ADDR", help="Left Vault address.")
@click.option("--left-token", required=True, envvar="VAULT_LEFT_TOKEN", help="Left Vault token.")
@click.option("--right-addr", required=True, envvar="VAULT_RIGHT_ADDR", help="Right Vault address.")
@click.option("--right-token", required=True, envvar="VAULT_RIGHT_TOKEN", help="Right Vault token.")
@click.option("--path", "paths", multiple=True, required=True, help="Secret path(s) to watch.")
@click.option("--interval", default=300, show_default=True, help="Seconds between runs.")
@click.option("--runs", default=None, type=int, help="Maximum number of runs (default: unlimited).")
@click.option("--output", default="text", type=click.Choice(["text", "json"]), show_default=True)
def schedule_command(
    left_addr: str,
    left_token: str,
    right_addr: str,
    right_token: str,
    paths: tuple,
    interval: int,
    runs: Optional[int],
    output: str,
) -> None:
    """Periodically compare Vault secret paths and print changes."""
    try:
        left = VaultClient(left_addr, left_token)
        right = VaultClient(right_addr, right_token)
    except VaultClientError as exc:
        click.echo(f"Vault connection error: {exc}", err=True)
        sys.exit(1)

    differ = VaultDiffer(left, right)

    def on_diff(path: str, diff: object) -> None:
        if output == "json":
            click.echo(json.dumps({"path": path, "diff": str(diff)}))
        else:
            click.echo(format_diff_text(path, diff, OutputFormat.TEXT))

    def on_error(path: str, exc: Exception) -> None:
        click.echo(f"[ERROR] {path}: {exc}", err=True)

    config = ScheduleConfig(
        paths=list(paths),
        interval_seconds=interval,
        max_runs=runs,
        on_diff=on_diff,
        on_error=on_error,
    )

    def diff_fn(path: str) -> object:
        return differ.diff_secret(path, path)

    scheduler = Scheduler(config, diff_fn)
    click.echo(f"Starting scheduler: {len(paths)} path(s), interval={interval}s", err=True)
    scheduler.run()
