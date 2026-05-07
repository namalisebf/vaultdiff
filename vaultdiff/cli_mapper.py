"""CLI command: vaultdiff map-paths — show how paths are rewritten by mapper rules."""
from __future__ import annotations

import json
import sys
from typing import List

import click

from vaultdiff.mapper import Mapper, MapperConfig, MapRule


@click.command("map-paths")
@click.argument("paths", nargs=-1, required=True)
@click.option("--prefix-from", multiple=True, metavar="OLD",
              help="Prefix to rewrite (paired with --prefix-to).")
@click.option("--prefix-to", multiple=True, metavar="NEW",
              help="Replacement prefix (paired with --prefix-from).")
@click.option("--format", "output_format", default="text",
              type=click.Choice(["text", "json"]), show_default=True,
              help="Output format.")
def map_paths_command(
    paths: List[str],
    prefix_from: List[str],
    prefix_to: List[str],
    output_format: str,
) -> None:
    """Show how each PATH is rewritten by the configured mapper rules."""
    if len(prefix_from) != len(prefix_to):
        click.echo(
            "error: --prefix-from and --prefix-to must be supplied in matching pairs.",
            err=True,
        )
        sys.exit(1)

    rules = [
        MapRule(pattern=old, replacement=new, mode="prefix")
        for old, new in zip(prefix_from, prefix_to)
    ]
    mapper = Mapper(MapperConfig(rules=rules))
    results = mapper.map_paths(list(paths))

    if output_format == "json":
        click.echo(json.dumps([r.to_dict() for r in results], indent=2))
        return

    for r in results:
        if r.rule_applied:
            click.echo(f"{r.original}  ->  {r.mapped}")
        else:
            click.echo(f"{r.original}  (unchanged)")
