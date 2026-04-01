"""``killpy list`` – print all detected environments to the terminal."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import click
from rich.console import Console
from rich.table import Table

from killpy.files import format_size
from killpy.models import Environment
from killpy.scanner import Scanner


def _filter_envs(
    envs: list[Environment],
    types: tuple[str, ...] | None,
    older_than: int | None,
) -> list[Environment]:
    now = datetime.now(tz=timezone.utc)
    result = envs

    if types:
        type_set = {t.strip().lower() for t in types}
        result = [e for e in result if e.type.lower() in type_set]

    if older_than is not None:
        cutoff = now - timedelta(days=older_than)
        result = [
            e for e in result if e.last_accessed.replace(tzinfo=timezone.utc) < cutoff
        ]

    return result


@click.command("list")
@click.option(
    "--path",
    default=Path.cwd,
    type=click.Path(path_type=Path, exists=True, file_okay=False, dir_okay=True),
    help="Root directory to scan.",
)
@click.option(
    "--type",
    "types",
    multiple=True,
    metavar="TYPE",
    help=(
        "Limit output to these environment types (repeatable). "
        "Example: --type venv --type conda"
    ),
)
@click.option(
    "--older-than",
    type=int,
    default=None,
    metavar="DAYS",
    help="Only show environments not accessed in the last N days.",
)
@click.option(
    "--json-stream",
    "as_json_stream",
    is_flag=True,
    default=False,
    help="Stream results as NDJSON (one JSON line per env) in real time.",
)
@click.option(
    "--json",
    "as_json",
    is_flag=True,
    default=False,
    help="Output as JSON array.",
)
def list_cmd(
    path: Path,
    types: tuple[str, ...],
    older_than: int | None,
    as_json: bool,
    as_json_stream: bool,
) -> None:
    """List all detected Python environments under PATH."""
    scanner = Scanner(types=set(types) if types else None)

    if as_json_stream:

        def _stream_progress(_detector, envs):
            for env in _filter_envs(envs, types or None, older_than):
                click.echo(json.dumps(env.to_dict()))

        scanner.scan(path, on_progress=_stream_progress)
        return

    envs = scanner.scan(path)
    envs = _filter_envs(envs, types or None, older_than)

    if as_json:
        click.echo(json.dumps([e.to_dict() for e in envs], indent=2))
        return

    if not envs:
        click.echo("No environments found.")
        return

    console = Console()
    table = Table(show_header=True, header_style="bold cyan")
    table.add_column("Type", style="dim", min_width=10)
    table.add_column("Name", min_width=20)
    table.add_column("Last accessed", min_width=12)
    table.add_column("Size", justify="right", min_width=9)
    table.add_column("Path")

    for env in envs:
        table.add_row(
            env.type,
            env.name,
            env.last_accessed_str,
            env.size_human,
            str(env.path),
        )

    console.print(table)
    total = sum(e.size_bytes for e in envs)
    console.print(
        f"\n[bold]{len(envs)}[/bold] environment(s) — "
        f"[bold]{format_size(total)}[/bold] total"
    )
