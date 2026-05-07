"""CLI command: stream secret diffs path-by-path."""
from __future__ import annotations

import json
import sys

import click

from vaultdiff.formatter import OutputFormat
from vaultdiff.streamer import StreamConfig, StreamEvent, Streamer
from vaultdiff.vault_client import VaultClient, VaultClientError


def _print_event(event: StreamEvent, fmt: OutputFormat) -> None:
    if fmt == OutputFormat.JSON:
        click.echo(json.dumps(event.to_dict()))
        return
    if event.has_error:
        click.echo(f"[ERROR] {event.path}: {event.error}", err=True)
        return
    diff = event.diff
    status = "CHANGED" if diff and diff.has_differences else "CLEAN"
    click.echo(f"[{status}] {event.path}")
    if diff:
        for key in sorted(diff.changed_keys):
            click.echo(f"  ~ {key}")
        for key in sorted(diff.only_in_left):
            click.echo(f"  - {key}")
        for key in sorted(diff.only_in_right):
            click.echo(f"  + {key}")


@click.command("stream")
@click.option("--left-addr", required=True, envvar="VAULT_LEFT_ADDR")
@click.option("--left-token", required=True, envvar="VAULT_LEFT_TOKEN")
@click.option("--right-addr", required=True, envvar="VAULT_RIGHT_ADDR")
@click.option("--right-token", required=True, envvar="VAULT_RIGHT_TOKEN")
@click.option("--path", "paths", multiple=True, required=True)
@click.option("--only-differences", is_flag=True, default=False)
@click.option("--stop-on-error", is_flag=True, default=False)
@click.option(
    "--format", "fmt",
    type=click.Choice(["text", "json"], case_sensitive=False),
    default="text",
)
@click.option("--exit-code", is_flag=True, default=False)
def stream_command(
    left_addr, left_token, right_addr, right_token,
    paths, only_differences, stop_on_error, fmt, exit_code
):
    """Stream secret diffs one path at a time, emitting events as they arrive."""
    fmt = OutputFormat(fmt)
    try:
        left = VaultClient(addr=left_addr, token=left_token)
        right = VaultClient(addr=right_addr, token=right_token)
    except VaultClientError as exc:
        click.echo(f"Vault error: {exc}", err=True)
        sys.exit(1)

    config = StreamConfig(
        paths=list(paths),
        stop_on_error=stop_on_error,
        only_differences=only_differences,
    )
    streamer = Streamer(left=left, right=right, config=config)
    found_diff = False
    found_error = False
    for event in streamer.stream():
        _print_event(event, fmt)
        if event.has_error:
            found_error = True
        elif event.diff and event.diff.has_differences:
            found_diff = True

    if found_error:
        sys.exit(1)
    if exit_code and found_diff:
        sys.exit(2)
