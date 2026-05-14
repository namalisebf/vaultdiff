"""CLI commands for the freezer: save and compare frozen diff states."""
from __future__ import annotations

import json
import sys

import click

from vaultdiff.vault_client import VaultClient, VaultClientError
from vaultdiff.differ import VaultDiffer
from vaultdiff.freezer import freeze_diffs, save_freeze, load_freeze


@click.group("freeze")
def freeze_command():
    """Freeze and compare secret diff states."""


@freeze_command.command("save")
@click.option("--left-addr", required=True, envvar="VAULT_LEFT_ADDR")
@click.option("--left-token", required=True, envvar="VAULT_LEFT_TOKEN")
@click.option("--right-addr", required=True, envvar="VAULT_RIGHT_ADDR")
@click.option("--right-token", required=True, envvar="VAULT_RIGHT_TOKEN")
@click.option("--path", "paths", multiple=True, required=True)
@click.option("--output", required=True, help="Destination file for frozen state.")
@click.option("--label", default="", help="Optional label for this freeze.")
def save_command(left_addr, left_token, right_addr, right_token, paths, output, label):
    """Capture and save a frozen diff state to a file."""
    try:
        left = VaultClient(left_addr, left_token)
        right = VaultClient(right_addr, right_token)
    except VaultClientError as exc:
        click.echo(f"Vault error: {exc}", err=True)
        sys.exit(1)

    differ = VaultDiffer(left, right)
    diffs = []
    for p in paths:
        try:
            diffs.append(differ.diff_secret(p))
        except VaultClientError as exc:
            click.echo(f"Error reading {p}: {exc}", err=True)
            sys.exit(1)

    report = freeze_diffs(diffs, label=label)
    save_freeze(report, output)
    click.echo(f"Frozen {len(diffs)} path(s) to {output}")


@freeze_command.command("check")
@click.option("--left-addr", required=True, envvar="VAULT_LEFT_ADDR")
@click.option("--left-token", required=True, envvar="VAULT_LEFT_TOKEN")
@click.option("--right-addr", required=True, envvar="VAULT_RIGHT_ADDR")
@click.option("--right-token", required=True, envvar="VAULT_RIGHT_TOKEN")
@click.option("--path", "paths", multiple=True, required=True)
@click.option("--baseline", required=True, help="Frozen baseline file to compare against.")
@click.option("--format", "fmt", default="text", type=click.Choice(["text", "json"]))
@click.option("--exit-code", is_flag=True, default=False)
def check_command(left_addr, left_token, right_addr, right_token, paths, baseline, fmt, exit_code):
    """Compare current diffs against a frozen baseline."""
    frozen = load_freeze(baseline)
    if frozen is None:
        click.echo(f"Baseline not found: {baseline}", err=True)
        sys.exit(1)

    frozen_paths = {e.path for e in frozen.entries}

    try:
        left = VaultClient(left_addr, left_token)
        right = VaultClient(right_addr, right_token)
    except VaultClientError as exc:
        click.echo(f"Vault error: {exc}", err=True)
        sys.exit(1)

    differ = VaultDiffer(left, right)
    new_diffs = []
    for p in paths:
        try:
            new_diffs.append(differ.diff_secret(p))
        except VaultClientError as exc:
            click.echo(f"Error reading {p}: {exc}", err=True)
            sys.exit(1)

    new_report = freeze_diffs(new_diffs)
    regressions = [
        e for e in new_report.dirty_entries() if e.path not in frozen_paths
        or not any(f.path == e.path and not f.has_differences() for f in frozen.entries)
    ]

    if fmt == "json":
        click.echo(json.dumps([e.to_dict() for e in regressions], indent=2))
    else:
        if not regressions:
            click.echo("No regressions detected.")
        else:
            for e in regressions:
                click.echo(f"[REGRESSION] {e.path}")

    if exit_code and regressions:
        sys.exit(1)
