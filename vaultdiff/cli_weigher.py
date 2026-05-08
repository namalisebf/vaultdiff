"""CLI command: vaultdiff weigh — show weight assigned to each secret path."""
from __future__ import annotations

import json
import sys

import click

from vaultdiff.vault_client import VaultClient, VaultClientError
from vaultdiff.differ import VaultDiffer
from vaultdiff.weigher import WeightConfig, WeightRule, weigh_diffs


@click.command("weigh")
@click.option("--left-addr", required=True, envvar="VAULT_LEFT_ADDR")
@click.option("--left-token", required=True, envvar="VAULT_LEFT_TOKEN")
@click.option("--right-addr", required=True, envvar="VAULT_RIGHT_ADDR")
@click.option("--right-token", required=True, envvar="VAULT_RIGHT_TOKEN")
@click.option("--path", "paths", multiple=True, required=True)
@click.option("--rule", "raw_rules", multiple=True, metavar="PATTERN:WEIGHT",
              help="Glob pattern and weight separated by colon, e.g. 'prod/*:5.0'")
@click.option("--default-weight", default=1.0, show_default=True, type=float)
@click.option("--format", "output_format", default="text", type=click.Choice(["text", "json"]))
def weigh_command(
    left_addr, left_token, right_addr, right_token,
    paths, raw_rules, default_weight, output_format,
):
    """Assign weights to secret paths based on pattern rules."""
    try:
        left = VaultClient(left_addr, left_token)
        right = VaultClient(right_addr, right_token)
    except VaultClientError as exc:
        click.echo(f"Vault error: {exc}", err=True)
        sys.exit(1)

    rules = []
    for raw in raw_rules:
        if ":" not in raw:
            click.echo(f"Invalid rule (expected PATTERN:WEIGHT): {raw}", err=True)
            sys.exit(1)
        pattern, _, weight_str = raw.rpartition(":")
        try:
            rules.append(WeightRule(pattern=pattern, weight=float(weight_str)))
        except ValueError:
            click.echo(f"Invalid weight value in rule: {raw}", err=True)
            sys.exit(1)

    config = WeightConfig(rules=rules, default_weight=default_weight)
    differ = VaultDiffer(left, right)

    try:
        diffs = [differ.diff_secret(p) for p in paths]
    except VaultClientError as exc:
        click.echo(f"Vault error: {exc}", err=True)
        sys.exit(1)

    weighed = weigh_diffs(diffs, config)

    if output_format == "json":
        click.echo(json.dumps([w.to_dict() for w in weighed], indent=2))
    else:
        for wp in weighed:
            rule_label = f" (rule: {wp.matched_rule})" if wp.matched_rule else ""
        for wp in weighed:
            rule_label = f" (rule: {wp.matched_rule})" if wp.matched_rule else ""
            click.echo(f"{wp.path}  weight={wp.weight:.2f}{rule_label}")
