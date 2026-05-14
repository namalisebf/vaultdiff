"""CLI command: rename — apply path rename rules to diff results."""
from __future__ import annotations

import json
import sys

import click

from vaultdiff.vault_client import VaultClient, VaultClientError
from vaultdiff.differ import VaultDiffer
from vaultdiff.renamer import RenameConfig, RenameRule, rename_diffs


@click.command("rename")
@click.option("--left-addr", required=True, envvar="VAULT_ADDR_LEFT")
@click.option("--left-token", required=True, envvar="VAULT_TOKEN_LEFT")
@click.option("--right-addr", required=True, envvar="VAULT_ADDR_RIGHT")
@click.option("--right-token", required=True, envvar="VAULT_TOKEN_RIGHT")
@click.option("--path", "paths", multiple=True, required=True)
@click.option(
    "--rule",
    "rules",
    multiple=True,
    help="Rename rule as 'pattern:replacement[:mode]'. mode defaults to prefix.",
)
@click.option("--format", "fmt", default="text", type=click.Choice(["text", "json"]))
def rename_command(
    left_addr: str,
    left_token: str,
    right_addr: str,
    right_token: str,
    paths: tuple,
    rules: tuple,
    fmt: str,
) -> None:
    """Diff secret paths and apply rename rules to the result paths."""
    parsed_rules = []
    for raw in rules:
        parts = raw.split(":")
        if len(parts) < 2:
            click.echo(f"Invalid rule (expected pattern:replacement[:mode]): {raw}", err=True)
            sys.exit(2)
        pattern, replacement = parts[0], parts[1]
        mode = parts[2] if len(parts) > 2 else "prefix"
        parsed_rules.append(RenameRule(pattern=pattern, replacement=replacement, mode=mode))

    config = RenameConfig(rules=parsed_rules)

    try:
        left = VaultClient(vault_addr=left_addr, vault_token=left_token)
        right = VaultClient(vault_addr=right_addr, vault_token=right_token)
    except VaultClientError as exc:
        click.echo(f"Vault client error: {exc}", err=True)
        sys.exit(1)

    differ = VaultDiffer(left, right)
    diffs = [differ.diff_secret(p) for p in paths]
    renamed = rename_diffs(diffs, config)

    if fmt == "json":
        click.echo(json.dumps([r.to_dict() for r in renamed], indent=2))
    else:
        for r in renamed:
            label = f"{r.original_path}"
            if r.rule_applied:
                label += f" -> {r.renamed_path}"
            changed = len(r.diff.changed_keys)
            left_only = len(r.diff.only_in_left)
            right_only = len(r.diff.only_in_right)
            click.echo(
                f"{label}  changed={changed} only_left={left_only} only_right={right_only}"
            )
