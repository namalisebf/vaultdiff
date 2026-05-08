"""CLI command: bucket — assign diffs into named buckets by rule."""

from __future__ import annotations

import json
import sys

import click

from vaultdiff.bucketer import BucketConfig, bucket_diffs
from vaultdiff.differ import VaultDiffer
from vaultdiff.formatter import OutputFormat
from vaultdiff.vault_client import VaultClient, VaultClientError


@click.command("bucket")
@click.option("--left-addr", required=True, envvar="VAULT_LEFT_ADDR")
@click.option("--left-token", required=True, envvar="VAULT_LEFT_TOKEN")
@click.option("--right-addr", required=True, envvar="VAULT_RIGHT_ADDR")
@click.option("--right-token", required=True, envvar="VAULT_RIGHT_TOKEN")
@click.option("--path", "paths", multiple=True, required=True)
@click.option("--rule", "rules", multiple=True, help="name:max_changed_keys[:path_prefix]")
@click.option("--default-bucket", default="default", show_default=True)
@click.option("--format", "fmt", type=click.Choice(["text", "json"]), default="text")
def bucket_command(
    left_addr, left_token, right_addr, right_token, paths, rules, default_bucket, fmt
):
    """Bucket secret diffs into named groups by rule."""
    try:
        left = VaultClient(left_addr, left_token)
        right = VaultClient(right_addr, right_token)
    except VaultClientError as exc:
        click.echo(f"Error: {exc}", err=True)
        sys.exit(1)

    parsed_rules = []
    for rule_str in rules:
        parts = rule_str.split(":")
        name = parts[0]
        max_ck = int(parts[1]) if len(parts) > 1 and parts[1] else None
        prefix = parts[2] if len(parts) > 2 else None
        from vaultdiff.bucketer import BucketRule
        parsed_rules.append(BucketRule(name=name, max_changed_keys=max_ck, path_prefix=prefix))

    config = BucketConfig(rules=parsed_rules, default_bucket=default_bucket)
    differ = VaultDiffer(left, right)

    diffs = []
    for path in paths:
        try:
            diffs.append(differ.diff_secret(path))
        except VaultClientError as exc:
            click.echo(f"Error reading {path}: {exc}", err=True)
            sys.exit(1)

    report = bucket_diffs(diffs, config)

    if fmt == "json":
        click.echo(json.dumps(report.to_dict(), indent=2))
    else:
        for name, bucket in report.buckets.items():
            click.echo(f"[{name}] ({bucket.total} paths)")
            for d in bucket.diffs:
                click.echo(f"  {d.path}")
