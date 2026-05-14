"""CLI command: collect — gather diff statistics across secret paths."""
from __future__ import annotations

import json
import sys

import click

from vaultdiff.vault_client import VaultClient, VaultClientError
from vaultdiff.differ import VaultDiffer
from vaultdiff.collector import collect_diffs


@click.command("collect")
@click.option("--left-addr", required=True, envvar="VAULT_LEFT_ADDR")
@click.option("--left-token", required=True, envvar="VAULT_LEFT_TOKEN")
@click.option("--right-addr", required=True, envvar="VAULT_RIGHT_ADDR")
@click.option("--right-token", required=True, envvar="VAULT_RIGHT_TOKEN")
@click.option("--path", "paths", multiple=True, required=True)
@click.option("--format", "fmt", type=click.Choice(["text", "json"]), default="text")
@click.option("--exit-code", is_flag=True, default=False)
def collect_command(left_addr, left_token, right_addr, right_token, paths, fmt, exit_code):
    """Collect diff statistics for one or more secret paths."""
    try:
        left = VaultClient(addr=left_addr, token=left_token)
        right = VaultClient(addr=right_addr, token=right_token)
    except VaultClientError as exc:
        click.echo(f"Vault error: {exc}", err=True)
        sys.exit(1)

    differ = VaultDiffer(left, right)
    diffs = []
    for p in paths:
        try:
            diffs.append(differ.diff_secret(p))
        except VaultClientError as exc:
            click.echo(f"Vault error reading {p}: {exc}", err=True)
            sys.exit(1)

    report = collect_diffs(diffs)

    if fmt == "json":
        click.echo(json.dumps(report.to_dict(), indent=2))
    else:
        click.echo(f"Paths: {report.total_paths}  Dirty: {report.dirty_paths}  Clean: {report.clean_paths}")
        for entry in report.entries:
            status = "DIRTY" if entry.has_differences() else "CLEAN"
            click.echo(
                f"  [{status}] {entry.path}  "
                f"changed={entry.changed_keys} "
                f"left_only={entry.only_in_left} "
                f"right_only={entry.only_in_right}"
            )

    if exit_code and report.dirty_paths > 0:
        sys.exit(1)
