"""CLI command: resolve — compare a secret path across N named environments."""
from __future__ import annotations

import json
import os
import sys

import click

from vaultdiff.vault_client import VaultClient, VaultClientError
from vaultdiff.resolver import resolve_paths


@click.command("resolve")
@click.argument("paths", nargs=-1, required=True)
@click.option(
    "--env",
    "envs",
    multiple=True,
    required=True,
    metavar="NAME=URL",
    help="Named environment in NAME=URL format. Repeat for multiple envs.",
)
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["text", "json"]),
    default="text",
    show_default=True,
)
@click.option("--exit-code", is_flag=True, default=False,
              help="Exit with code 1 if any inconsistencies or missing paths are found.")
@click.pass_context
def resolve_command(ctx: click.Context, paths, envs, output_format, exit_code):
    """Resolve secret PATHS across multiple Vault environments."""
    clients = {}
    for spec in envs:
        if "=" not in spec:
            click.echo(f"Invalid --env value '{spec}'. Expected NAME=URL.", err=True)
            sys.exit(2)
        name, url = spec.split("=", 1)
        token_var = f"VAULT_TOKEN_{name.upper()}"
        token = os.environ.get(token_var) or os.environ.get("VAULT_TOKEN", "")
        try:
            clients[name] = VaultClient(url=url, token=token)
        except VaultClientError as exc:
            click.echo(f"Vault client error for env '{name}': {exc}", err=True)
            sys.exit(1)

    try:
        report = resolve_paths(clients, list(paths))
    except VaultClientError as exc:
        click.echo(f"Vault error: {exc}", err=True)
        sys.exit(1)

    if output_format == "json":
        click.echo(json.dumps(report.to_dict(), indent=2))
    else:
        for rp in report.paths:
            status = "OK" if rp.is_consistent else "INCONSISTENT"
            if rp.missing_from:
                status = f"MISSING in {', '.join(rp.missing_from)}"
            click.echo(f"{rp.path}  [{status}]")
            for env, data in rp.envs.items():
                keys = ", ".join(sorted(data.keys())) if data else "<not found>"
                click.echo(f"  {env}: {keys}")

    if exit_code and (report.inconsistent_paths or report.missing_paths):
        sys.exit(1)
