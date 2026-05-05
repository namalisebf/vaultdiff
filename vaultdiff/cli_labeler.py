"""CLI command for labeling Vault secret paths."""

from __future__ import annotations

import json
import sys

import click

from vaultdiff.labeler import LabelConfig, LabelRule, Labeler
from vaultdiff.vault_client import VaultClient, VaultClientError


@click.command("label")
@click.option("--left-addr", required=True, envvar="VAULT_LEFT_ADDR", help="Left Vault address.")
@click.option("--left-token", required=True, envvar="VAULT_LEFT_TOKEN", help="Left Vault token.")
@click.option("--path", "paths", multiple=True, required=True, help="Secret paths to label.")
@click.option("--label-rule", "raw_rules", multiple=True,
              help="Label rule as LABEL:PATTERN or LABEL:PATTERN:MODE.")
@click.option("--format", "output_format", default="text",
              type=click.Choice(["text", "json"]), show_default=True)
def label_command(
    left_addr: str,
    left_token: str,
    paths: tuple,
    raw_rules: tuple,
    output_format: str,
) -> None:
    """Label secret paths according to configurable rules."""
    rules = []
    for raw in raw_rules:
        parts = raw.split(":", 2)
        if len(parts) < 2:
            click.echo(f"Invalid rule (expected LABEL:PATTERN): {raw}", err=True)
            sys.exit(2)
        label, pattern = parts[0], parts[1]
        mode = parts[2] if len(parts) == 3 else "glob"
        rules.append(LabelRule(label=label, pattern=pattern, mode=mode))

    config = LabelConfig(rules=rules)
    labeler = Labeler(config)

    try:
        client = VaultClient(addr=left_addr, token=left_token)
        # Validate connectivity by listing the first path
        client.list_secrets(paths[0])
    except VaultClientError as exc:
        click.echo(f"Vault error: {exc}", err=True)
        sys.exit(1)

    labeled = labeler.label_paths(list(paths))

    if output_format == "json":
        click.echo(json.dumps([lp.to_dict() for lp in labeled], indent=2))
    else:
        for lp in labeled:
            tag_str = ", ".join(lp.labels) if lp.labels else "(none)"
            click.echo(f"{lp.path}  [{tag_str}]")
