"""CLI entry point for vaultdiff."""
from __future__ import annotations

import sys
import click

from vaultdiff.vault_client import VaultClient, VaultClientError
from vaultdiff.differ import VaultDiffer
from vaultdiff.filter import FilterConfig
from vaultdiff.formatter import OutputFormat
from vaultdiff.reporter import Reporter


@click.group()
def cli() -> None:
    """vaultdiff — compare HashiCorp Vault secrets across environments."""


@cli.command("diff")
@click.option("--left-addr", required=True, envvar="VAULT_LEFT_ADDR", help="Left Vault address.")
@click.option("--left-token", required=True, envvar="VAULT_LEFT_TOKEN", help="Left Vault token.")
@click.option("--right-addr", required=True, envvar="VAULT_RIGHT_ADDR", help="Right Vault address.")
@click.option("--right-token", required=True, envvar="VAULT_RIGHT_TOKEN", help="Right Vault token.")
@click.option("--path", "paths", multiple=True, help="Secret path(s) to compare.")
@click.option("--recursive", is_flag=True, default=False, help="Recursively compare all paths under mount.")
@click.option("--mount", default=None, help="Mount prefix for recursive mode.")
@click.option("--format", "output_format", default="text", type=click.Choice(["text", "json"]), show_default=True)
@click.option("--exit-code", is_flag=True, default=False, help="Exit with code 1 when differences are found.")
@click.option("--include-path", "include_paths", multiple=True, help="Glob pattern to include paths.")
@click.option("--exclude-path", "exclude_paths", multiple=True, help="Glob pattern to exclude paths.")
@click.option("--include-key", "include_keys", multiple=True, help="Glob pattern to include keys.")
@click.option("--exclude-key", "exclude_keys", multiple=True, help="Glob pattern to exclude keys.")
@click.option("--regex", is_flag=True, default=False, help="Treat filter patterns as regular expressions.")
def diff_command(
    left_addr, left_token, right_addr, right_token,
    paths, recursive, mount, output_format, exit_code,
    include_paths, exclude_paths, include_keys, exclude_keys, regex,
) -> None:
    """Compare secret paths between two Vault instances."""
    fmt = OutputFormat(output_format)
    filter_cfg = FilterConfig(
        include_paths=list(include_paths),
        exclude_paths=list(exclude_paths),
        include_keys=list(include_keys),
        exclude_keys=list(exclude_keys),
        regex=regex,
    )
    try:
        left_client = VaultClient(left_addr, left_token)
        right_client = VaultClient(right_addr, right_token)
    except VaultClientError as exc:
        click.echo(f"Error: {exc}", err=True)
        sys.exit(2)

    differ = VaultDiffer(left_client, right_client, filter_config=filter_cfg)
    reporter = Reporter(differ, output_format=fmt)

    try:
        if recursive:
            if not mount:
                click.echo("Error: --mount is required with --recursive.", err=True)
                sys.exit(2)
            has_diffs = reporter.report_recursive(mount)
        else:
            if not paths:
                click.echo("Error: provide at least one --path or use --recursive.", err=True)
                sys.exit(2)
            has_diffs = reporter.report_paths(list(paths))
    except VaultClientError as exc:
        click.echo(f"Error: {exc}", err=True)
        sys.exit(2)

    if exit_code and has_diffs:
        sys.exit(1)


def main() -> None:
    cli()


if __name__ == "__main__":
    main()
