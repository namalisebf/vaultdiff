"""CLI command for the dispatcher: show which handler each path routes to."""
from __future__ import annotations

import json
import sys
from typing import List, Optional

import click

from vaultdiff.dispatcher import DispatchConfig, DispatchRule, Dispatcher
from vaultdiff.differ import SecretDiff, VaultDiffer
from vaultdiff.vault_client import VaultClient, VaultClientError


@click.command("dispatch")
@click.option("--left-addr", envvar="VAULT_LEFT_ADDR", required=True)
@click.option("--left-token", envvar="VAULT_LEFT_TOKEN", required=True)
@click.option("--right-addr", envvar="VAULT_RIGHT_ADDR", required=True)
@click.option("--right-token", envvar="VAULT_RIGHT_TOKEN", required=True)
@click.option("--path", "paths", multiple=True, required=True)
@click.option("--rule", "raw_rules", multiple=True,
              help="name:pattern or name:pattern:mode")
@click.option("--default-handler", default="default", show_default=True)
@click.option("--format", "fmt", type=click.Choice(["text", "json"]),
              default="text", show_default=True)
def dispatch_command(
    left_addr, left_token, right_addr, right_token,
    paths, raw_rules, default_handler, fmt,
):
    """Show which dispatch handler each Vault path routes to."""
    try:
        left = VaultClient(left_addr, left_token)
        right = VaultClient(right_addr, right_token)
    except VaultClientError as exc:
        click.echo(f"Error: {exc}", err=True)
        sys.exit(1)

    rules = []
    for raw in raw_rules:
        parts = raw.split(":")
        if len(parts) < 2:
            click.echo(f"Invalid rule '{raw}' — expected name:pattern[:mode]", err=True)
            sys.exit(1)
        name, pattern = parts[0], parts[1]
        mode = parts[2] if len(parts) > 2 else "glob"
        rules.append(DispatchRule(name=name, pattern=pattern, mode=mode))

    config = DispatchConfig(rules=rules, default_handler=default_handler)
    dispatcher = Dispatcher(config)
    differ = VaultDiffer(left, right)

    diffs: List[SecretDiff] = []
    for p in paths:
        try:
            diffs.append(differ.diff_secret(p))
        except VaultClientError as exc:
            click.echo(f"Error reading '{p}': {exc}", err=True)
            sys.exit(1)

    report = dispatcher.dispatch(diffs)

    if fmt == "json":
        click.echo(json.dumps(report.to_dict(), indent=2))
    else:
        for handler_name, bucket in sorted(report.dispatched.items()):
            for diff in bucket:
                click.echo(f"{diff.path}  ->  {handler_name}")
