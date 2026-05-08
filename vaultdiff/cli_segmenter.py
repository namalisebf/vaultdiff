"""CLI command for segmenting vault diff results into named buckets."""
from __future__ import annotations

import json
import sys

import click

from vaultdiff.cli import diff_command  # noqa: F401 – ensure group registered
from vaultdiff.formatter import OutputFormat
from vaultdiff.segmenter import SegmentConfig, SegmentRule, segment_diffs
from vaultdiff.vault_client import VaultClient, VaultClientError
from vaultdiff.differ import VaultDiffer


@click.command("segment")
@click.option("--left-addr", required=True, envvar="VAULT_LEFT_ADDR")
@click.option("--left-token", required=True, envvar="VAULT_LEFT_TOKEN")
@click.option("--right-addr", required=True, envvar="VAULT_RIGHT_ADDR")
@click.option("--right-token", required=True, envvar="VAULT_RIGHT_TOKEN")
@click.option("--path", "paths", multiple=True, required=True)
@click.option("--segment", "segment_defs", multiple=True,
              help="name:prefix=<prefix> or name:glob=<pattern>")
@click.option("--default-segment", default="default", show_default=True)
@click.option("--format", "fmt", type=click.Choice(["text", "json"]), default="text")
@click.pass_context
def segment_command(ctx, left_addr, left_token, right_addr, right_token,
                   paths, segment_defs, default_segment, fmt):
    """Segment diff results across paths into named buckets."""
    try:
        left = VaultClient(left_addr, left_token)
        right = VaultClient(right_addr, right_token)
    except VaultClientError as exc:
        click.echo(f"Vault error: {exc}", err=True)
        sys.exit(1)

    rules = []
    for defn in segment_defs:
        try:
            name, rest = defn.split(":", 1)
            key, value = rest.split("=", 1)
            if key == "prefix":
                rules.append(SegmentRule(name=name, prefix=value))
            elif key == "glob":
                rules.append(SegmentRule(name=name, glob=value))
            else:
                click.echo(f"Unknown segment key '{key}' in '{defn}'", err=True)
                sys.exit(1)
        except ValueError:
            click.echo(f"Invalid segment definition '{defn}'", err=True)
            sys.exit(1)

    config = SegmentConfig(rules=rules, default_segment=default_segment)
    differ = VaultDiffer(left, right)

    diffs = []
    for path in paths:
        try:
            diffs.append(differ.diff_secret(path))
        except VaultClientError as exc:
            click.echo(f"Error reading '{path}': {exc}", err=True)
            sys.exit(1)

    report = segment_diffs(diffs, config)

    if fmt == "json":
        click.echo(json.dumps(report.to_dict(), indent=2))
    else:
        for name, seg in report.segments.items():
            status = f"{seg.dirty} dirty / {seg.total} total"
            click.echo(f"[{name}] {status}")
            for d in seg.diffs:
                marker = "*" if d.has_differences else " "
                click.echo(f"  {marker} {d.path}")
