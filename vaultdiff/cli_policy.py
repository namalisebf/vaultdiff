"""CLI sub-command: vaultdiff policy-check — enforce key/value policies on diffs."""
from __future__ import annotations

import json
import sys

import click

from vaultdiff.vault_client import VaultClient, VaultClientError
from vaultdiff.differ import VaultDiffer
from vaultdiff.policy import PolicyChecker, PolicyConfig


@click.command("policy-check")
@click.option("--path", "paths", multiple=True, required=True, help="Secret path(s) to check.")
@click.option("--addr-left", required=True, envvar="VAULT_ADDR_LEFT")
@click.option("--addr-right", required=True, envvar="VAULT_ADDR_RIGHT")
@click.option("--token-left", required=True, envvar="VAULT_TOKEN_LEFT")
@click.option("--token-right", required=True, envvar="VAULT_TOKEN_RIGHT")
@click.option("--required-key-pattern", default=None, help="Regex that all keys must match.")
@click.option("--forbidden-key-pattern", default=None, help="Regex that no key may match.")
@click.option("--max-value-length", default=None, type=int, help="Maximum allowed value length.")
@click.option("--disallow-empty", is_flag=True, default=False, help="Fail on empty values.")
@click.option("--output", type=click.Choice(["text", "json"]), default="text")
@click.option("--exit-code", is_flag=True, default=False,
              help="Exit with code 2 when violations are found.")
def policy_check_command(
    paths, addr_left, addr_right, token_left, token_right,
    required_key_pattern, forbidden_key_pattern, max_value_length,
    disallow_empty, output, exit_code,
):
    """Check that secrets on PATH conform to naming and value policies."""
    try:
        left = VaultClient(addr_left, token_left)
        right = VaultClient(addr_right, token_right)
    except VaultClientError as exc:
        click.echo(f"Vault connection error: {exc}", err=True)
        sys.exit(1)

    config = PolicyConfig(
        required_key_pattern=required_key_pattern,
        forbidden_key_pattern=forbidden_key_pattern,
        max_value_length=max_value_length,
        disallow_empty_values=disallow_empty,
    )
    checker = PolicyChecker(config)
    differ = VaultDiffer(left, right)

    all_violations = []
    for path in paths:
        try:
            diff = differ.diff_secret(path)
        except VaultClientError as exc:
            click.echo(f"Error reading '{path}': {exc}", err=True)
            sys.exit(1)
        all_violations.extend(checker.check_diff(diff))

    if output == "json":
        click.echo(json.dumps([v.to_dict() for v in all_violations], indent=2))
    else:
        if not all_violations:
            click.echo("No policy violations found.")
        else:
            for v in all_violations:
                click.echo(
                    f"[{v.rule}] {v.path} :: {v.key} — {v.message}"
                )

    if exit_code and all_violations:
        sys.exit(2)
