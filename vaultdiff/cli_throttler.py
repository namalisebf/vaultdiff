"""CLI sub-command: throttle-info — display throttle configuration and stats."""
from __future__ import annotations

import json
import sys

import click

from vaultdiff.throttler import ThrottleConfig, Throttler
from vaultdiff.vault_client import VaultClient, VaultClientError


@click.command("throttle-info")
@click.option("--left-addr", envvar="VAULT_ADDR_LEFT", required=True, help="Left Vault address.")
@click.option("--left-token", envvar="VAULT_TOKEN_LEFT", required=True, help="Left Vault token.")
@click.option("--path", "paths", multiple=True, required=True, help="Secret paths to read.")
@click.option("--max-rps", default=10.0, show_default=True, help="Max requests per second.")
@click.option("--burst", default=1, show_default=True, help="Burst size (token bucket).")
@click.option("--format", "fmt", type=click.Choice(["text", "json"]), default="text", show_default=True)
def throttle_info_command(
    left_addr: str,
    left_token: str,
    paths: tuple,
    max_rps: float,
    burst: int,
    fmt: str,
) -> None:
    """Read secrets through a throttled client and report throttle statistics."""
    cfg = ThrottleConfig(max_calls_per_second=max_rps, burst=burst, enabled=True)
    throttler = Throttler(cfg)

    try:
        client = VaultClient(addr=left_addr, token=left_token)
    except VaultClientError as exc:
        click.echo(f"Error: {exc}", err=True)
        sys.exit(1)

    results = []
    for path in paths:
        throttler.acquire()
        try:
            data = client.read_secret(path)
            results.append({"path": path, "keys": list(data.keys())})
        except VaultClientError as exc:
            click.echo(f"Warning: could not read {path!r}: {exc}", err=True)

    stats = throttler.stats.to_dict()

    if fmt == "json":
        click.echo(json.dumps({"stats": stats, "paths": results}, indent=2))
    else:
        click.echo(f"Paths read   : {stats['total_calls']}")
        click.echo(f"Throttled    : {stats['throttled_calls']}")
        click.echo(f"Total wait   : {stats['total_wait_seconds']:.4f}s")
        for r in results:
            click.echo(f"  {r['path']} -> {len(r['keys'])} key(s)")
