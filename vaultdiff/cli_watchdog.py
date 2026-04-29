"""CLI command: vaultdiff watchdog — continuously watch Vault paths for drift."""
import json
import sys
import time

import click

from vaultdiff.vault_client import VaultClient, VaultClientError
from vaultdiff.differ import VaultDiffer
from vaultdiff.snapshot import load_snapshot
from vaultdiff.watchdog import Watchdog, WatchdogConfig, WatchEvent


def _print_event(event: WatchEvent, fmt: str) -> None:
    if fmt == "json":
        click.echo(json.dumps(event.to_dict()))
    else:
        click.echo(f"[CHANGE] {event.path}")
        for entry in event.drift_entries:
            if entry.has_drift():
                click.echo(f"  key={entry.key} status={entry.status}")


@click.command("watchdog")
@click.option("--addr-left", envvar="VAULT_ADDR_LEFT", required=True)
@click.option("--token-left", envvar="VAULT_TOKEN_LEFT", required=True)
@click.option("--baseline", "baseline_file", required=True, help="Path to baseline snapshot JSON")
@click.option("--path", "paths", multiple=True, required=True)
@click.option("--interval", default=60, show_default=True, help="Poll interval in seconds")
@click.option("--once", is_flag=True, default=False, help="Run a single check and exit")
@click.option("--format", "fmt", type=click.Choice(["text", "json"]), default="text")
def watchdog_command(
    addr_left: str,
    token_left: str,
    baseline_file: str,
    paths: tuple,
    interval: int,
    once: bool,
    fmt: str,
) -> None:
    """Watch Vault paths against a baseline snapshot and report drift."""
    try:
        client = VaultClient(addr_left, token_left)
    except VaultClientError as exc:
        click.echo(f"Vault error: {exc}", err=True)
        sys.exit(1)

    try:
        snapshot = load_snapshot(baseline_file)
    except FileNotFoundError:
        click.echo(f"Baseline file not found: {baseline_file}", err=True)
        sys.exit(1)

    differ = VaultDiffer(client, client)
    config = WatchdogConfig(
        paths=list(paths),
        baseline_snapshot=snapshot,
        on_change=lambda ev: _print_event(ev, fmt),
        on_error=lambda p, e: click.echo(f"Error checking {p}: {e}", err=True),
    )
    watchdog = Watchdog(config, differ)

    if once:
        watchdog.run_once()
        return

    while True:
        watchdog.run_once()
        time.sleep(interval)
