"""CLI commands for pinning secret values and checking deviations."""
from __future__ import annotations

import json
import sys

import click

from vaultdiff.vault_client import VaultClient, VaultClientError
from vaultdiff.differ import VaultDiffer
from vaultdiff.pinner import check_pins, load_pins, save_pins


@click.group("pin")
def pin_command() -> None:
    """Pin and verify secret key values."""


@pin_command.command("save")
@click.option("--left-addr", envvar="VAULT_LEFT_ADDR", required=True)
@click.option("--left-token", envvar="VAULT_LEFT_TOKEN", required=True)
@click.option("--path", "secret_path", required=True, help="Secret path to pin.")
@click.option("--output", required=True, help="File to write pins to.")
def save_command(left_addr: str, left_token: str, secret_path: str, output: str) -> None:
    """Capture current left-side values as pins."""
    try:
        client = VaultClient(url=left_addr, token=left_token)
        data = client.read_secret(secret_path)
    except VaultClientError as exc:
        click.echo(f"Vault error: {exc}", err=True)
        sys.exit(1)

    pins = {secret_path: {k: str(v) for k, v in data.items()}}
    save_pins(pins, output)
    click.echo(f"Pinned {len(data)} key(s) from '{secret_path}' to {output}")


@pin_command.command("check")
@click.option("--left-addr", envvar="VAULT_LEFT_ADDR", required=True)
@click.option("--left-token", envvar="VAULT_LEFT_TOKEN", required=True)
@click.option("--right-addr", envvar="VAULT_RIGHT_ADDR", required=True)
@click.option("--right-token", envvar="VAULT_RIGHT_TOKEN", required=True)
@click.option("--pins", "pins_file", required=True, help="Pin file to check against.")
@click.option("--format", "fmt", default="text", type=click.Choice(["text", "json"]))
@click.option("--exit-code", is_flag=True, default=False)
def check_command(
    left_addr: str, left_token: str, right_addr: str, right_token: str,
    pins_file: str, fmt: str, exit_code: bool,
) -> None:
    """Check live secrets against pinned values."""
    try:
        pins_data = load_pins(pins_file)
    except FileNotFoundError as exc:
        click.echo(str(exc), err=True)
        sys.exit(1)

    try:
        left = VaultClient(url=left_addr, token=left_token)
        right = VaultClient(url=right_addr, token=right_token)
        differ = VaultDiffer(left, right)
    except VaultClientError as exc:
        click.echo(f"Vault error: {exc}", err=True)
        sys.exit(1)

    any_deviation = False
    reports = []
    for path, pinned_keys in pins_data.items():
        try:
            diff = differ.diff_secret(path)
        except VaultClientError as exc:
            click.echo(f"Vault error on '{path}': {exc}", err=True)
            sys.exit(1)
        report = check_pins(diff, pinned_keys)
        reports.append(report)
        if report.has_deviations:
            any_deviation = True

    if fmt == "json":
        click.echo(json.dumps([r.to_dict() for r in reports], indent=2))
    else:
        for report in reports:
            status = "DEVIATED" if report.has_deviations else "OK"
            click.echo(f"{report.path}: {status}")
            for pin in report.pins:
                marker = "!" if pin.deviated else " "
                click.echo(f"  [{marker}] {pin.key}: pinned={pin.pinned_value!r} current={pin.current_value!r}")

    if exit_code and any_deviation:
        sys.exit(1)
