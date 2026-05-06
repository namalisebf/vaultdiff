"""CLI command: vaultdiff profile — show volatility profile for secret paths."""
from __future__ import annotations

import json
import sys
from typing import List

import click

from vaultdiff.vault_client import VaultClient, VaultClientError
from vaultdiff.differ import VaultDiffer
from vaultdiff.profiler import profile_diffs, PathProfile
from vaultdiff.formatter import OutputFormat


def _print_text(profiles: List[PathProfile]) -> None:
    if not profiles:
        click.echo("No paths profiled.")
        return
    click.echo(f"{'PATH':<45} {'CATEGORY':<10} {'VOLATILITY':>10} {'CHANGED':>8}")
    click.echo("-" * 80)
    for p in profiles:
        click.echo(
            f"{p.path:<45} {p.category:<10} {p.volatility:>10.2%} {p.changed_keys:>8}"
        )


@click.command("profile")
@click.option("--left-addr", required=True, envvar="VAULT_LEFT_ADDR")
@click.option("--left-token", required=True, envvar="VAULT_LEFT_TOKEN")
@click.option("--right-addr", required=True, envvar="VAULT_RIGHT_ADDR")
@click.option("--right-token", required=True, envvar="VAULT_RIGHT_TOKEN")
@click.option("--path", "paths", multiple=True, required=True)
@click.option(
    "--format",
    "fmt",
    type=click.Choice(["text", "json"]),
    default="text",
    show_default=True,
)
@click.option("--recursive", is_flag=True, default=False)
def profile_command(
    left_addr, left_token, right_addr, right_token, paths, fmt, recursive
):
    """Profile secret paths and report volatility metrics."""
    try:
        left = VaultClient(url=left_addr, token=left_token)
        right = VaultClient(url=right_addr, token=right_token)
    except VaultClientError as exc:
        click.echo(f"Vault connection error: {exc}", err=True)
        sys.exit(1)

    differ = VaultDiffer(left, right)
    diffs = []

    try:
        for path in paths:
            if recursive:
                diffs.extend(differ.diff_recursive(path))
            else:
                diffs.append(differ.diff_secret(path))
    except VaultClientError as exc:
        click.echo(f"Vault error: {exc}", err=True)
        sys.exit(1)

    profiles = profile_diffs(diffs)

    if fmt == "json":
        click.echo(json.dumps([p.to_dict() for p in profiles], indent=2))
    else:
        _print_text(profiles)
