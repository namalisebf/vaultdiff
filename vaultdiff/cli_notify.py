"""CLI sub-command for sending audit notifications."""

from __future__ import annotations

import click

from vaultdiff.auditor import Auditor
from vaultdiff.differ import VaultDiffer
from vaultdiff.notifier import Notifier, NotifierConfig, NotifierError
from vaultdiff.vault_client import VaultClient, VaultClientError


@click.command("notify")
@click.option("--left-addr", required=True, envvar="VAULT_LEFT_ADDR", help="Left Vault address.")
@click.option("--left-token", required=True, envvar="VAULT_LEFT_TOKEN", help="Left Vault token.")
@click.option("--right-addr", required=True, envvar="VAULT_RIGHT_ADDR", help="Right Vault address.")
@click.option("--right-token", required=True, envvar="VAULT_RIGHT_TOKEN", help="Right Vault token.")
@click.option("--webhook-url", required=True, envvar="VAULTDIFF_WEBHOOK_URL", help="Webhook URL.")
@click.option("--slack-channel", default=None, envvar="VAULTDIFF_SLACK_CHANNEL", help="Slack channel.")
@click.option("--always", is_flag=True, default=False, help="Notify even when no differences found.")
@click.argument("paths", nargs=-1, required=True)
def notify_command(
    left_addr: str,
    left_token: str,
    right_addr: str,
    right_token: str,
    webhook_url: str,
    slack_channel: str | None,
    always: bool,
    paths: tuple[str, ...],
) -> None:
    """Diff PATHS and dispatch results to a webhook."""
    try:
        left_client = VaultClient(addr=left_addr, token=left_token)
        right_client = VaultClient(addr=right_addr, token=right_token)
    except VaultClientError as exc:
        raise click.ClickException(str(exc)) from exc

    differ = VaultDiffer(left_client, right_client)
    auditor = Auditor()

    for path in paths:
        diff = differ.diff_secret(path)
        auditor.record(path, diff)

    config = NotifierConfig(
        webhook_url=webhook_url,
        slack_channel=slack_channel,
        only_on_differences=not always,
    )
    notifier = Notifier(config)

    try:
        notifier.send(auditor.entries)
    except NotifierError as exc:
        raise click.ClickException(str(exc)) from exc

    click.echo(f"Notification dispatched for {len(auditor.entries)} path(s).")
