"""CLI sub-command: vaultdiff compare — run a structured multi-path comparison."""
from __future__ import annotations

import json
import sys
from typing import Optional, Tuple

import click

from vaultdiff.comparator import Comparator
from vaultdiff.differ import VaultDiffer
from vaultdiff.filter import FilterConfig
from vaultdiff.vault_client import VaultClient, VaultClientError


@click.command("compare")
@click.option("--left-addr", envvar="VAULT_LEFT_ADDR", required=True, help="Left Vault address.")
@click.option("--left-token", envvar="VAULT_LEFT_TOKEN", required=True, help="Left Vault token.")
@click.option("--right-addr", envvar="VAULT_RIGHT_ADDR", required=True, help="Right Vault address.")
@click.option("--right-token", envvar="VAULT_RIGHT_TOKEN", required=True, help="Right Vault token.")
@click.option("--path", "paths", multiple=True, required=False, help="Paths to compare (repeatable).")
@click.option("--recursive", "root", default=None, help="Recursively compare all paths under root.")
@click.option("--include", "includes", multiple=True, help="Include glob patterns for paths.")
@click.option("--exclude", "excludes", multiple=True, help="Exclude glob patterns for paths.")
@click.option("--exit-code", is_flag=True, default=False, help="Exit 1 if differences found.")
@click.option("--format", "fmt", type=click.Choice(["text", "json"]), default="text")
def compare_command(
    left_addr: str,
    left_token: str,
    right_addr: str,
    right_token: str,
    paths: Tuple[str, ...],
    root: Optional[str],
    includes: Tuple[str, ...],
    excludes: Tuple[str, ...],
    exit_code: bool,
    fmt: str,
) -> None:
    """Compare one or more Vault secret paths and report a structured result."""
    if not paths and not root:
        raise click.UsageError("Provide --path or --recursive.")

    try:
        left = VaultClient(url=left_addr, token=left_token)
        right = VaultClient(url=right_addr, token=right_token)
    except VaultClientError as exc:
        click.echo(f"Vault connection error: {exc}", err=True)
        sys.exit(1)

    filter_cfg: Optional[FilterConfig] = None
    if includes or excludes:
        filter_cfg = FilterConfig(
            include_paths=list(includes),
            exclude_paths=list(excludes),
        )

    differ = VaultDiffer(left, right)
    comparator = Comparator(differ, filter_config=filter_cfg)

    try:
        if root:
            result = comparator.compare_recursive(root)
        else:
            result = comparator.compare(list(paths))
    except VaultClientError as exc:
        click.echo(f"Vault error: {exc}", err=True)
        sys.exit(1)

    if fmt == "json":
        click.echo(json.dumps(result.to_dict(), indent=2))
    else:
        status = "PASS" if result.passed else "FAIL"
        click.echo(f"Result: {status}")
        for p in result.changed_paths:
            click.echo(f"  CHANGED  {p}")
        for p in result.clean_paths:
            click.echo(f"  CLEAN    {p}")
        for p, err in result.errors.items():
            click.echo(f"  ERROR    {p}: {err}")

    if exit_code and not result.passed:
        sys.exit(1)
