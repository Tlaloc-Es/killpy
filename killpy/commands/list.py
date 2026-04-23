"""``killpy list`` – print all detected environments to the terminal."""

from __future__ import annotations

import json
from pathlib import Path

import click
from rich.console import Console
from rich.table import Table

from killpy.commands._utils import filter_envs
from killpy.files import format_size
from killpy.scanner import Scanner


def _run_json_stream(
    scanner: Scanner,
    path: Path,
    types: tuple[str, ...],
    older_than: int | None,
    quiet: bool,
    stderr_console: Console,
) -> None:
    if not quiet:
        stderr_console.print("[dim]Scanning…[/dim]")

    def _progress(detector, envs):
        if not quiet:
            stderr_console.print(
                f"[dim]  {detector.name}[/dim] — [dim]{len(envs)} found[/dim]",
            )
        for env in filter_envs(envs, types or None, older_than):
            click.echo(json.dumps(env.to_dict()))

    scanner.scan(path, on_progress=_progress)


def _scan_with_progress(
    scanner: Scanner, path: Path, quiet: bool, stderr_console: Console
):
    if quiet:
        return scanner.scan(path)

    status = stderr_console.status("Scanning…", spinner="dots")
    status.start()

    def _progress(detector, _envs):
        status.update(f"Scanning… [dim]{detector.name}[/dim]")

    envs = scanner.scan(path, on_progress=_progress)
    status.stop()
    return envs


def _print_table(envs: list, console: Console) -> None:
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
@click.option(
    "--quiet",
    "-q",
    is_flag=True,
    default=False,
    help="Suppress progress messages (useful in scripts/pipelines).",
)
def list_cmd(
    path: Path,
    types: tuple[str, ...],
    older_than: int | None,
    as_json: bool,
    as_json_stream: bool,
    quiet: bool,
) -> None:
    """List all detected Python environments under PATH."""
    scanner = Scanner(types=set(types) if types else None)
    stderr_console = Console(stderr=True)

    if as_json_stream:
        _run_json_stream(scanner, path, types, older_than, quiet, stderr_console)
        return

    envs = _scan_with_progress(scanner, path, quiet, stderr_console)
    envs = filter_envs(envs, types or None, older_than)

    if as_json:
        click.echo(json.dumps([e.to_dict() for e in envs], indent=2))
        return

    if not envs:
        click.echo("No environments found.")
        return

    _print_table(envs, Console())
