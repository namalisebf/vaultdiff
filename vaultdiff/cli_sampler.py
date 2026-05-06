"""cli_sampler.py — CLI command for randomly sampling secret paths."""
from __future__ import annotations

import json
import sys

import click

from vaultdiff.vault_client import VaultClient, VaultClientError
from vaultdiff.differ import VaultDiffer
from vaultdiff.formatter import OutputFormat, format_diff_text
from vaultdiff.sampler import SampleConfig, sample_diffs


@click.command("sample")
@click.option("--left-addr", required=True, envvar="VAULT_LEFT_ADDR", help="Left Vault address.")
@click.option("--left-token", required=True, envvar="VAULT_LEFT_TOKEN", help="Left Vault token.")
@click.option("--right-addr", required=True, envvar="VAULT_RIGHT_ADDR", help="Right Vault address.")
@click.option("--right-token", required=True, envvar="VAULT_RIGHT_TOKEN", help="Right Vault token.")
@click.option("--path", "paths", multiple=True, required=True, help="Secret path(s) to consider.")
@click.option("--max-paths", default=10, show_default=True, help="Maximum paths to sample.")
@click.option("--fraction", default=None, type=float, help="Fraction of paths to sample (0.0–1.0).")
@click.option("--seed", default=None, type=int, help="Random seed for reproducibility.")
@click.option("--format", "fmt", type=click.Choice(["text", "json"]), default="text", show_default=True)
def sample_command(
    left_addr, left_token, right_addr, right_token,
    paths, max_paths, fraction, seed, fmt,
):
    """Randomly sample a subset of secret paths and show their diffs."""
    try:
        left = VaultClient(addr=left_addr, token=left_token)
        right = VaultClient(addr=right_addr, token=right_token)
    except VaultClientError as exc:
        click.echo(f"Vault error: {exc}", err=True)
        sys.exit(1)

    differ = VaultDiffer(left, right)
    config = SampleConfig(seed=seed, max_paths=max_paths, fraction=fraction)

    try:
        all_diffs = [differ.diff_secret(p) for p in paths]
    except VaultClientError as exc:
        click.echo(f"Vault error: {exc}", err=True)
        sys.exit(1)

    report = sample_diffs(all_diffs, config)

    if fmt == "json":
        click.echo(json.dumps(report.to_dict(), indent=2))
        return

    click.echo(
        f"Sampled {report.sample_size}/{report.total_available} paths "
        f"(coverage={report.coverage:.1%}, seed={report.seed})"
    )
    for diff in report.selected:
        text = format_diff_text(diff, output_format=OutputFormat.TEXT)
        click.echo(text)
