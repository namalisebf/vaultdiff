"""CLI command for routing secret diffs to named destinations."""
from __future__ import annotations

import json
import sys

import click

from vaultdiff.vault_client import VaultClient, VaultClientError
from vaultdiff.differ import VaultDiffer
from vaultdiff.router import RouteConfig, RouteRule, route_diffs


@click.command("route")
@click.option("--left-addr", required=True, envvar="VAULT_LEFT_ADDR")
@click.option("--left-token", required=True, envvar="VAULT_LEFT_TOKEN")
@click.option("--right-addr", required=True, envvar="VAULT_RIGHT_ADDR")
@click.option("--right-token", required=True, envvar="VAULT_RIGHT_TOKEN")
@click.option("--path", "paths", multiple=True, required=True)
@click.option("--dest", "dest_rules", multiple=True,
              help="prefix:destination or glob:destination routing rules")
@click.option("--default-dest", default="default", show_default=True)
@click.option("--format", "fmt", type=click.Choice(["text", "json"]), default="text")
def route_command(
    left_addr, left_token, right_addr, right_token,
    paths, dest_rules, default_dest, fmt
):
    """Route diffs across secret paths to named destinations."""
    try:
        left = VaultClient(left_addr, left_token)
        right = VaultClient(right_addr, right_token)
    except VaultClientError as exc:
        click.echo(f"Error: {exc}", err=True)
        sys.exit(1)

    rules = []
    for rule_str in dest_rules:
        if ":" not in rule_str:
            click.echo(f"Invalid rule (expected pattern:destination): {rule_str}", err=True)
            sys.exit(1)
        pattern, destination = rule_str.split(":", 1)
        if "*" in pattern or "?" in pattern:
            rules.append(RouteRule(destination=destination, glob=pattern))
        else:
            rules.append(RouteRule(destination=destination, prefix=pattern))

    config = RouteConfig(rules=rules, default_destination=default_dest)
    differ = VaultDiffer(left, right)

    try:
        diffs = [differ.diff_secret(p) for p in paths]
    except VaultClientError as exc:
        click.echo(f"Error: {exc}", err=True)
        sys.exit(1)

    report = route_diffs(diffs, config)

    if fmt == "json":
        click.echo(json.dumps(report.to_dict(), indent=2))
    else:
        for dest in report.destinations:
            dest_diffs = report.diffs_for(dest)
            click.echo(f"[{dest}]")
            for d in dest_diffs:
                marker = "*" if d.has_differences() else " "
                click.echo(f"  {marker} {d.path}")
