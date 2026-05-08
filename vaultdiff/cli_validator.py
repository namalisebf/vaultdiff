"""CLI command for validating secret diffs against schema rules."""
from __future__ import annotations

import json
import sys
from typing import Optional

import click

from vaultdiff.vault_client import VaultClient, VaultClientError
from vaultdiff.differ import VaultDiffer
from vaultdiff.validator import Validator, ValidationConfig
from vaultdiff.formatter import OutputFormat


@click.command("validate")
@click.option("--left-addr", required=True, envvar="VAULT_LEFT_ADDR")
@click.option("--left-token", required=True, envvar="VAULT_LEFT_TOKEN")
@click.option("--right-addr", required=True, envvar="VAULT_RIGHT_ADDR")
@click.option("--right-token", required=True, envvar="VAULT_RIGHT_TOKEN")
@click.option("--path", "paths", multiple=True, required=True)
@click.option("--config", "config_file", type=click.Path(exists=True), default=None)
@click.option("--format", "fmt", type=click.Choice(["text", "json"]), default="text")
@click.option("--exit-code", is_flag=True, default=False)
@click.pass_context
def validate_command(
    ctx: click.Context,
    left_addr: str,
    left_token: str,
    right_addr: str,
    right_token: str,
    paths: tuple,
    config_file: Optional[str],
    fmt: str,
    exit_code: bool,
) -> None:
    """Validate secret diffs against schema rules."""
    config_data: dict = {}
    if config_file:
        with open(config_file) as fh:
            config_data = json.load(fh)

    config = ValidationConfig.from_dict(config_data)
    validator = Validator(config)

    try:
        left = VaultClient(left_addr, left_token)
        right = VaultClient(right_addr, right_token)
    except VaultClientError as exc:
        click.echo(f"Error: {exc}", err=True)
        sys.exit(1)

    differ = VaultDiffer(left, right)
    all_violations = []

    for path in paths:
        try:
            diff = differ.diff_secret(path)
            violations = validator.validate(diff)
            all_violations.extend(violations)
        except VaultClientError as exc:
            click.echo(f"Error reading '{path}': {exc}", err=True)
            sys.exit(1)

    if fmt == "json":
        click.echo(json.dumps([v.to_dict() for v in all_violations], indent=2))
    else:
        if not all_violations:
            click.echo("All paths passed validation.")
        else:
            for v in all_violations:
                click.echo(f"[{v.path}] {v.message} (rule: {v.rule_glob})")

    if exit_code and all_violations:
        sys.exit(1)
