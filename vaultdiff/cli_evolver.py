"""CLI command for tracking secret diff evolution across labeled snapshots."""
from __future__ import annotations

import json
import sys
from typing import List, Tuple

import click

from vaultdiff.vault_client import VaultClient, VaultClientError
from vaultdiff.differ import VaultDiffer
from vaultdiff.evolver import evolve_diffs, EvolutionTrack


def _print_text(tracks: List[EvolutionTrack]) -> None:
    if not tracks:
        click.echo("No evolution data.")
        return
    for track in tracks:
        trend = "growing" if track.is_growing() else ("stable" if track.is_stable() else "fluctuating")
        click.echo(f"  {track.path}  [{trend}]")
        for pt in track.points:
            click.echo(
                f"    {pt.label}: changed={pt.changed_keys} "
                f"left_only={pt.only_in_left} right_only={pt.only_in_right} "
                f"total={pt.total_differences}"
            )


@click.command("evolve")
@click.option("--left-token", envvar="VAULT_LEFT_TOKEN", required=True)
@click.option("--right-token", envvar="VAULT_RIGHT_TOKEN", required=True)
@click.option("--left-addr", envvar="VAULT_LEFT_ADDR", required=True)
@click.option("--right-addr", envvar="VAULT_RIGHT_ADDR", required=True)
@click.option("--path", "paths", multiple=True, required=True, help="Secret paths to track.")
@click.option(
    "--snapshot",
    "snapshots",
    multiple=True,
    metavar="LABEL:LEFT_MOUNT:RIGHT_MOUNT",
    required=True,
    help="Snapshot definition as label:left_mount:right_mount.",
)
@click.option("--format", "fmt", type=click.Choice(["text", "json"]), default="text")
def evolve_command(
    left_token: str,
    right_token: str,
    left_addr: str,
    right_addr: str,
    paths: Tuple[str, ...],
    snapshots: Tuple[str, ...],
    fmt: str,
) -> None:
    """Show how diff counts evolve across labelled snapshot pairs."""
    try:
        left_client = VaultClient(addr=left_addr, token=left_token)
        right_client = VaultClient(addr=right_addr, token=right_token)
    except VaultClientError as exc:
        click.echo(f"Vault error: {exc}", err=True)
        sys.exit(1)

    differ = VaultDiffer(left_client, right_client)
    labeled: List[tuple] = []

    for snap in snapshots:
        parts = snap.split(":", 2)
        if len(parts) != 3:
            click.echo(f"Invalid snapshot format: {snap}", err=True)
            sys.exit(1)
        label, left_mount, right_mount = parts
        diffs = [differ.diff_secret(f"{left_mount}/{p}", f"{right_mount}/{p}") for p in paths]
        labeled.append((label, diffs))

    tracks = evolve_diffs(labeled)

    if fmt == "json":
        click.echo(json.dumps([t.to_dict() for t in tracks], indent=2))
    else:
        _print_text(tracks)
