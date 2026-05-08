"""CLI command for correlating secret diffs across environments."""
from __future__ import annotations

import json
import sys
from typing import List, Tuple

import click

from vaultdiff.correlator import correlate_diffs
from vaultdiff.differ import VaultDiffer
from vaultdiff.vault_client import VaultClient, VaultClientError


def _parse_env_pair(value: str) -> Tuple[str, str]:
    """Parse 'name=url' into (name, url)."""
    if "=" not in value:
        raise click.BadParameter(f"Expected format NAME=URL, got: {value!r}")
    name, _, url = value.partition("=")
    return name.strip(), url.strip()


@click.command("correlate")
@click.option("--env", "envs", multiple=True, required=True,
              metavar="NAME=VAULT_ADDR",
              help="Environment name and Vault address (repeatable).")
@click.option("--token", "tokens", multiple=True, required=True,
              metavar="NAME=TOKEN",
              help="Vault token for each environment (repeatable).")
@click.option("--path", "paths", multiple=True, required=True,
              help="Secret paths to correlate (repeatable).")
@click.option("--format", "output_format", default="text",
              type=click.Choice(["text", "json"]), show_default=True)
@click.option("--universal-only", is_flag=True, default=False,
              help="Only show keys that changed in every environment.")
def correlate_command(
    envs: List[str],
    tokens: List[str],
    paths: List[str],
    output_format: str,
    universal_only: bool,
) -> None:
    """Correlate key-level changes across multiple Vault environments."""
    try:
        env_map = dict(_parse_env_pair(e) for e in envs)
        token_map = dict(_parse_env_pair(t) for t in tokens)
    except click.BadParameter as exc:
        click.echo(str(exc), err=True)
        sys.exit(1)

    env_diffs = {}
    try:
        for env_name, vault_addr in env_map.items():
            token = token_map.get(env_name, "")
            client = VaultClient(url=vault_addr, token=token)
            differ = VaultDiffer(client, client)
            diffs = [differ.diff_secret(p, p) for p in paths]
            env_diffs[env_name] = diffs
    except VaultClientError as exc:
        click.echo(f"Vault error: {exc}", err=True)
        sys.exit(1)

    report = correlate_diffs(env_diffs)

    if output_format == "json":
        click.echo(json.dumps(report.to_dict(), indent=2))
        return

    for cp in report.paths:
        keys_to_show = cp.universal_change_keys if universal_only else cp.keys
        if not keys_to_show:
            continue
        click.echo(f"\nPath: {cp.path}")
        for ck in keys_to_show:
            tag = "[universal]" if ck.is_universal_change else "[partial]"
            click.echo(f"  {tag} {ck.key}: changed in {', '.join(ck.environments_changed)}")
