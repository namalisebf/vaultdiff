"""CLI command: generate a patch plan from two Vault paths."""
from __future__ import annotations

import json
import sys

import click

from vaultdiff.vault_client import VaultClient, VaultClientError
from vaultdiff.differ import VaultDiffer
from vaultdiff.patcher import build_patches
from vaultdiff.formatter import OutputFormat


@click.command("patch")
@click.argument("path", nargs=-1, required=True)
@click.option("--left-addr", envvar="VAULT_LEFT_ADDR", required=True)
@click.option("--left-token", envvar="VAULT_LEFT_TOKEN", required=True)
@click.option("--right-addr", envvar="VAULT_RIGHT_ADDR", required=True)
@click.option("--right-token", envvar="VAULT_RIGHT_TOKEN", required=True)
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["text", "json"]),
    default="text",
    show_default=True,
)
@click.option("--exit-code", is_flag=True, default=False,
              help="Exit with code 1 when any ops are generated.")
def patch_command(
    path,
    left_addr, left_token,
    right_addr, right_token,
    output_format,
    exit_code,
):
    """Generate a patch plan to reconcile PATH(s) from left to right Vault."""
    try:
        left = VaultClient(left_addr, left_token)
        right = VaultClient(right_addr, right_token)
    except VaultClientError as exc:
        click.echo(f"Vault error: {exc}", err=True)
        sys.exit(1)

    differ = VaultDiffer(left, right)

    try:
        diffs = [differ.diff_secret(p) for p in path]
    except VaultClientError as exc:
        click.echo(f"Vault error: {exc}", err=True)
        sys.exit(1)

    plans = build_patches(diffs)

    if output_format == "json":
        click.echo(json.dumps([p.to_dict() for p in plans], indent=2))
    else:
        if not plans:
            click.echo("No patch operations required.")
        for plan in plans:
            click.echo(f"Path: {plan.path}")
            for op in plan.ops:
                if op.operation == "set":
                    old = f" (was: {op.old_value!r})" if op.old_value is not None else ""
                    click.echo(f"  SET   {op.key} = {op.value!r}{old}")
                elif op.operation == "delete":
                    click.echo(f"  DEL   {op.key}")

    if exit_code and plans:
        sys.exit(1)
