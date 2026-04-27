"""CLI commands for baseline snapshot management."""

from __future__ import annotations

import sys
from typing import Optional

import click

from vaultdiff.baseline import (
    BaselineEntry,
    compare_to_baseline,
    load_baseline,
    save_baseline,
)
from vaultdiff.differ import VaultDiffer
from vaultdiff.reporter import Reporter
from vaultdiff.vault_client import VaultClient, VaultClientError


@click.group("baseline")
def baseline_command() -> None:
    """Manage diff baselines for regression detection."""


@baseline_command.command("save")
@click.option("--left-addr", required=True, envvar="VAULT_LEFT_ADDR")
@click.option("--right-addr", required=True, envvar="VAULT_RIGHT_ADDR")
@click.option("--left-token", required=True, envvar="VAULT_LEFT_TOKEN")
@click.option("--right-token", required=True, envvar="VAULT_RIGHT_TOKEN")
@click.option("--path", "paths", required=True, multiple=True)
@click.option("--output", required=True, help="Path to write baseline JSON file.")
@click.option("--recursive", is_flag=True, default=False)
def save_command(
    left_addr: str,
    right_addr: str,
    left_token: str,
    right_token: str,
    paths: tuple,
    output: str,
    recursive: bool,
) -> None:
    """Snapshot current diffs into a baseline file."""
    try:
        left = VaultClient(left_addr, left_token)
        right = VaultClient(right_addr, right_token)
    except VaultClientError as exc:
        click.echo(f"Error: {exc}", err=True)
        sys.exit(1)

    differ = VaultDiffer(left, right)
    entries: list[BaselineEntry] = []

    for path in paths:
        if recursive:
            diffs = differ.diff_recursive(path)
        else:
            diffs = {path: differ.diff_secret(path)}

        for p, diff in diffs.items():
            entries.append(BaselineEntry.from_diff(p, diff))

    save_baseline(output, entries)
    click.echo(f"Baseline saved to {output} ({len(entries)} path(s))")


@baseline_command.command("check")
@click.option("--left-addr", required=True, envvar="VAULT_LEFT_ADDR")
@click.option("--right-addr", required=True, envvar="VAULT_RIGHT_ADDR")
@click.option("--left-token", required=True, envvar="VAULT_LEFT_TOKEN")
@click.option("--right-token", required=True, envvar="VAULT_RIGHT_TOKEN")
@click.option("--path", "paths", required=True, multiple=True)
@click.option("--baseline", "baseline_file", required=True)
@click.option("--recursive", is_flag=True, default=False)
def check_command(
    left_addr: str,
    right_addr: str,
    left_token: str,
    right_token: str,
    paths: tuple,
    baseline_file: str,
    recursive: bool,
) -> None:
    """Check current diffs against a saved baseline."""
    try:
        baseline = load_baseline(baseline_file)
    except FileNotFoundError as exc:
        click.echo(f"Error: {exc}", err=True)
        sys.exit(1)

    try:
        left = VaultClient(left_addr, left_token)
        right = VaultClient(right_addr, right_token)
    except VaultClientError as exc:
        click.echo(f"Error: {exc}", err=True)
        sys.exit(1)

    differ = VaultDiffer(left, right)
    current: dict = {}

    for path in paths:
        if recursive:
            current.update(differ.diff_recursive(path))
        else:
            current[path] = differ.diff_secret(path)

    regressions = compare_to_baseline(current, baseline)

    if not regressions:
        click.echo("No regressions detected.")
        sys.exit(0)

    click.echo(f"Regressions detected in {len(regressions)} path(s):", err=True)
    for path, issues in regressions.items():
        for issue in issues:
            click.echo(f"  {path}: {issue}", err=True)
    sys.exit(1)
