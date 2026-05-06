"""CLI command for tracing secret change history across labelled diff sets."""
from __future__ import annotations

import json
import sys
from typing import List, Optional, Tuple

import click

from vaultdiff.differ import VaultDiffer
from vaultdiff.tracer import build_trace_report
from vaultdiff.vault_client import VaultClient, VaultClientError


def _parse_env_pair(value: str) -> Tuple[str, str, str]:
    """Parse 'label:addr1:addr2' into (label, addr1, addr2)."""
    parts = value.split(":", 2)
    if len(parts) != 3:
        raise click.BadParameter(
            f"Expected format label:left_addr:right_addr, got: {value!r}"
        )
    return parts[0], parts[1], parts[2]


@click.command("trace")
@click.option(
    "--env",
    "envs",
    multiple=True,
    required=True,
    metavar="LABEL:LEFT:RIGHT",
    help="Labelled environment pair in format label:left_addr:right_addr.",
)
@click.option("--path", "paths", multiple=True, required=True, help="Secret paths to trace.")
@click.option("--token", envvar="VAULT_TOKEN", required=True, help="Vault token.")
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["text", "json"]),
    default="text",
    show_default=True,
)
def trace_command(
    envs: Tuple[str, ...],
    paths: Tuple[str, ...],
    token: str,
    output_format: str,
) -> None:
    """Trace secret changes across multiple labelled environment pairs."""
    from collections import defaultdict

    labelled_diffs = {}

    for env_spec in envs:
        try:
            label, left_addr, right_addr = _parse_env_pair(env_spec)
        except click.BadParameter as exc:
            click.echo(str(exc), err=True)
            sys.exit(1)

        try:
            left = VaultClient(url=left_addr, token=token)
            right = VaultClient(url=right_addr, token=token)
        except VaultClientError as exc:
            click.echo(f"Vault error: {exc}", err=True)
            sys.exit(1)

        differ = VaultDiffer(left, right)
        diffs = []
        for path in paths:
            try:
                diffs.append(differ.diff_secret(path))
            except VaultClientError as exc:
                click.echo(f"Error reading {path}: {exc}", err=True)
                sys.exit(1)

        labelled_diffs[label] = diffs

    report = build_trace_report(labelled_diffs)

    if output_format == "json":
        click.echo(json.dumps(report.to_dict(), indent=2))
    else:
        click.echo(f"Total changes: {report.total_changes}")
        for point in report.points:
            status = "CHANGED" if point.has_changes else "CLEAN"
            click.echo(f"  [{point.label}] {point.path}: {status}")
            for k in point.changed_keys:
                click.echo(f"    ~ {k}")
            for k in point.only_in_left:
                click.echo(f"    - {k}")
            for k in point.only_in_right:
                click.echo(f"    + {k}")
