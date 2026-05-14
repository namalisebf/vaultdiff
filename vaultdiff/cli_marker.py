"""CLI command for marking diff paths with configurable labels."""
from __future__ import annotations

import json
import sys

import click

from vaultdiff.marker import MarkConfig, MarkRule, mark_diffs
from vaultdiff.reporter import Reporter
from vaultdiff.vault_client import VaultClient, VaultClientError


@click.command("mark")
@click.option("--left-addr", required=True, envvar="VAULT_LEFT_ADDR")
@click.option("--left-token", required=True, envvar="VAULT_LEFT_TOKEN")
@click.option("--right-addr", required=True, envvar="VAULT_RIGHT_ADDR")
@click.option("--right-token", required=True, envvar="VAULT_RIGHT_TOKEN")
@click.option("--path", "paths", multiple=True, required=True)
@click.option("--mark-rule", "mark_rules", multiple=True, metavar="PATTERN:MARK",
              help="Glob pattern and mark separated by colon, e.g. 'prod/*:production'")
@click.option("--default-mark", default="", show_default=True)
@click.option("--format", "output_format", type=click.Choice(["text", "json"]), default="text")
@click.option("--recursive", is_flag=True, default=False)
def mark_command(
    left_addr, left_token, right_addr, right_token,
    paths, mark_rules, default_mark, output_format, recursive,
):
    """Mark diff paths with labels based on pattern rules."""
    try:
        left = VaultClient(left_addr, left_token)
        right = VaultClient(right_addr, right_token)
    except VaultClientError as exc:
        click.echo(f"Vault error: {exc}", err=True)
        sys.exit(1)

    rules = []
    for raw in mark_rules:
        if ":" not in raw:
            click.echo(f"Invalid --mark-rule '{raw}': expected PATTERN:MARK", err=True)
            sys.exit(1)
        pattern, mark = raw.split(":", 1)
        rules.append(MarkRule(pattern=pattern, mark=mark))

    config = MarkConfig(rules=rules, default_mark=default_mark)

    from vaultdiff.differ import VaultDiffer
    differ = VaultDiffer(left, right)

    try:
        if recursive:
            diffs = [differ.diff_secret(p) for p in differ.diff_paths(list(paths))]
        else:
            diffs = [differ.diff_secret(p) for p in paths]
    except VaultClientError as exc:
        click.echo(f"Vault error: {exc}", err=True)
        sys.exit(1)

    report = mark_diffs(diffs, config)

    if output_format == "json":
        click.echo(json.dumps(report.to_dict(), indent=2))
        return

    for entry in report.entries:
        mark_label = f"[{entry.mark}]" if entry.mark else "[unmarked]"
        status = "DIRTY" if entry.has_differences() else "clean"
        click.echo(f"{mark_label} {entry.path}: {status}")
