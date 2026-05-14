"""CLI command for environment-aware diff tagging."""
from __future__ import annotations

import json
import sys

import click

from vaultdiff.tagger2 import EnvTagConfig, EnvTagRule, tag_diffs
from vaultdiff.vault_client import VaultClient, VaultClientError
from vaultdiff.differ import VaultDiffer


@click.command("tag2")
@click.option("--left-addr", required=True, envvar="VAULT_LEFT_ADDR")
@click.option("--left-token", required=True, envvar="VAULT_LEFT_TOKEN")
@click.option("--right-addr", required=True, envvar="VAULT_RIGHT_ADDR")
@click.option("--right-token", required=True, envvar="VAULT_RIGHT_TOKEN")
@click.option("--path", "paths", multiple=True, required=True)
@click.option("--env", default=None, help="Environment label for rule matching")
@click.option("--tag", "tag_rules", multiple=True, metavar="PATTERN:TAG",
              help="Add a tag rule as pattern:tag")
@click.option("--format", "fmt", type=click.Choice(["text", "json"]), default="text")
def tag2_command(
    left_addr, left_token, right_addr, right_token, paths, env, tag_rules, fmt
):
    """Tag diff results with environment-aware labels."""
    try:
        left = VaultClient(left_addr, left_token)
        right = VaultClient(right_addr, right_token)
    except VaultClientError as exc:
        click.echo(f"Error: {exc}", err=True)
        sys.exit(1)

    rules = []
    for rule_str in tag_rules:
        if ":" not in rule_str:
            click.echo(f"Invalid tag rule (expected pattern:tag): {rule_str}", err=True)
            sys.exit(1)
        pattern, tag = rule_str.split(":", 1)
        rules.append(EnvTagRule(pattern=pattern, tag=tag))

    config = EnvTagConfig(rules=rules)
    differ = VaultDiffer(left, right)

    try:
        diffs = [differ.diff_secret(p) for p in paths]
    except VaultClientError as exc:
        click.echo(f"Error: {exc}", err=True)
        sys.exit(1)

    tagged = tag_diffs(diffs, config, env=env)

    if fmt == "json":
        click.echo(json.dumps([t.to_dict() for t in tagged], indent=2))
    else:
        for t in tagged:
            status = "DIRTY" if t.diff.has_differences() else "clean"
        click.echo(f"{t.path}  [{t.tag}]  {status}")
