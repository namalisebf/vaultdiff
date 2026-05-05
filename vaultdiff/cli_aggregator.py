"""CLI command for aggregating diffs across multiple environment pairs."""

import json
from typing import List, Optional, Tuple

import click

from vaultdiff.aggregator import aggregate_diffs
from vaultdiff.differ import VaultDiffer
from vaultdiff.vault_client import VaultClient, VaultClientError


@click.command("aggregate")
@click.option("--paths", required=True, multiple=True, help="Secret paths to compare.")
@click.option(
    "--env",
    "envs",
    required=True,
    multiple=True,
    metavar="LABEL:LEFT_ADDR:RIGHT_ADDR",
    help="Environment definition as label:left_vault_addr:right_vault_addr.",
)
@click.option("--token", envvar="VAULT_TOKEN", required=True, help="Vault token.")
@click.option(
    "--format",
    "output_format",
    default="text",
    type=click.Choice(["text", "json"]),
    show_default=True,
)
@click.option(
    "--exit-code",
    is_flag=True,
    default=False,
    help="Exit with code 1 if any differences found.",
)
@click.pass_context
def aggregate_command(
    ctx: click.Context,
    paths: Tuple[str, ...],
    envs: Tuple[str, ...],
    token: str,
    output_format: str,
    exit_code: bool,
) -> None:
    """Compare secret paths across multiple Vault environment pairs."""
    parsed = _parse_envs(envs)
    if not parsed:
        click.echo("Error: no valid --env definitions provided.", err=True)
        ctx.exit(1)

    env_diffs: dict = {}
    try:
        for label, left_addr, right_addr in parsed:
            left = VaultClient(addr=left_addr, token=token)
            right = VaultClient(addr=right_addr, token=token)
            differ = VaultDiffer(left, right)
            env_diffs[label] = {
                path: differ.diff_secret(path) for path in paths
            }
    except VaultClientError as exc:
        click.echo(f"Vault error: {exc}", err=True)
        ctx.exit(1)

    report = aggregate_diffs(env_diffs)

    if output_format == "json":
        click.echo(json.dumps(report.to_dict(), indent=2))
    else:
        _print_text(report)

    if exit_code and report.dirty_paths:
        ctx.exit(1)


def _parse_envs(envs: Tuple[str, ...]) -> List[Tuple[str, str, str]]:
    result = []
    for env in envs:
        parts = env.split(":", 2)
        if len(parts) == 3:
            result.append((parts[0], parts[1], parts[2]))
    return result


def _print_text(report) -> None:
    click.echo(f"Environments: {', '.join(report.environments)}")
    click.echo(f"Paths: {len(report.paths)} total, {len(report.dirty_paths)} with differences")
    for agg in report.paths:
        status = "DIFF" if agg.has_differences() else "CLEAN"
        click.echo(
            f"  [{status}] {agg.path} "
            f"(changed={agg.total_changed}, "
            f"left_only={agg.total_only_in_left}, "
            f"right_only={agg.total_only_in_right})"
        )
