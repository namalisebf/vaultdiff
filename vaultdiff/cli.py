"""Command-line interface for vaultdiff."""

import sys
import click

from vaultdiff.vault_client import VaultClient, VaultClientError
from vaultdiff.differ import VaultDiffer
from vaultdiff.formatter import OutputFormat
from vaultdiff.reporter import Reporter


@click.group()
@click.version_option()
def cli():
    """Compare and audit HashiCorp Vault secret paths across environments."""


@cli.command("diff")
@click.argument("left_path")
@click.argument("right_path")
@click.option("--left-url", envvar="VAULT_LEFT_ADDR", required=True, help="Vault URL for left side.")
@click.option("--right-url", envvar="VAULT_RIGHT_ADDR", required=True, help="Vault URL for right side.")
@click.option("--left-token", envvar="VAULT_LEFT_TOKEN", required=True, help="Vault token for left side.")
@click.option("--right-token", envvar="VAULT_RIGHT_TOKEN", required=True, help="Vault token for right side.")
@click.option("--format", "output_format", type=click.Choice([f.value for f in OutputFormat]), default=OutputFormat.TEXT.value, show_default=True)
@click.option("--recursive", "-r", is_flag=True, default=False, help="Recursively diff all secrets under the path.")
@click.option("--exit-code", is_flag=True, default=False, help="Exit with code 1 if differences found.")
def diff_command(left_path, right_path, left_url, right_url, left_token, right_token, output_format, recursive, exit_code):
    """Diff secrets at LEFT_PATH and RIGHT_PATH across two Vault instances."""
    fmt = OutputFormat(output_format)
    try:
        left_client = VaultClient(url=left_url, token=left_token)
        right_client = VaultClient(url=right_url, token=right_token)
    except VaultClientError as exc:
        click.echo(f"Error connecting to Vault: {exc}", err=True)
        sys.exit(2)

    differ = VaultDiffer(left_client, right_client)
    reporter = Reporter(differ, output_format=fmt)

    try:
        if recursive:
            has_diff = reporter.report_recursive(left_path, right_path)
        else:
            has_diff = reporter.report_path(left_path, right_path)
    except VaultClientError as exc:
        click.echo(f"Vault error: {exc}", err=True)
        sys.exit(2)

    if exit_code and has_diff:
        sys.exit(1)


def main():
    cli()


if __name__ == "__main__":
    main()
