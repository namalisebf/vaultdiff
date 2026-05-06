"""CLI command: annotate — attach notes to diff paths using annotation rules."""

from __future__ import annotations

import json
import sys

import click

from vaultdiff.annotator import AnnotationConfig, AnnotationRule, annotate_diffs
from vaultdiff.differ import VaultDiffer
from vaultdiff.formatter import OutputFormat
from vaultdiff.vault_client import VaultClient, VaultClientError


@click.command("annotate")
@click.option("--left-addr", required=True, envvar="VAULT_LEFT_ADDR", help="Left Vault address.")
@click.option("--left-token", required=True, envvar="VAULT_LEFT_TOKEN", help="Left Vault token.")
@click.option("--right-addr", required=True, envvar="VAULT_RIGHT_ADDR", help="Right Vault address.")
@click.option("--right-token", required=True, envvar="VAULT_RIGHT_TOKEN", help="Right Vault token.")
@click.option("--path", "paths", multiple=True, required=True, help="Secret path(s) to compare.")
@click.option(
    "--note",
    "raw_notes",
    multiple=True,
    metavar="PATTERN:NOTE",
    help="Annotation rule as PATTERN:NOTE (glob by default).",
)
@click.option("--format", "fmt", type=click.Choice(["text", "json"]), default="text")
def annotate_command(
    left_addr: str,
    left_token: str,
    right_addr: str,
    right_token: str,
    paths: tuple,
    raw_notes: tuple,
    fmt: str,
) -> None:
    """Compare paths and attach annotation notes based on path patterns."""
    rules = []
    for raw in raw_notes:
        if ":" not in raw:
            click.echo(f"Invalid --note value (expected PATTERN:NOTE): {raw}", err=True)
            sys.exit(2)
        pattern, note = raw.split(":", 1)
        rules.append(AnnotationRule(pattern=pattern, note=note))

    config = AnnotationConfig(rules=rules)

    try:
        left = VaultClient(vault_addr=left_addr, vault_token=left_token)
        right = VaultClient(vault_addr=right_addr, vault_token=right_token)
    except VaultClientError as exc:
        click.echo(f"Vault client error: {exc}", err=True)
        sys.exit(1)

    differ = VaultDiffer(left_client=left, right_client=right)

    pairs = []
    for path in paths:
        try:
            diff = differ.diff_secret(path)
            pairs.append((path, diff))
        except VaultClientError as exc:
            click.echo(f"Error reading {path}: {exc}", err=True)
            sys.exit(1)

    annotated = annotate_diffs(pairs, config)

    if fmt == "json":
        click.echo(json.dumps([a.to_dict() for a in annotated], indent=2))
    else:
        for ap in annotated:
            status = "DIFF" if ap.diff.has_differences() else "CLEAN"
            notes_str = ", ".join(ap.notes) if ap.notes else "(no notes)"
            click.echo(f"[{status}] {ap.path}  —  {notes_str}")
