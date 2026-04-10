"""``killpy delete`` – non-interactively remove detected environments."""

from __future__ import annotations

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import click
from rich.console import Console

from killpy.cleaner import Cleaner, CleanerError
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
            e for e in result if e.last_accessed < cutoff
        ]

    return result


@click.command("delete")
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
        "Limit deletion to these environment types (repeatable). "
        "Example: --type venv --type conda"
    ),
)
@click.option(
    "--older-than",
    type=int,
    default=None,
    metavar="DAYS",
    help="Only delete environments not accessed in the last N days.",
)
@click.option(
    "--dry-run",
    is_flag=True,
    default=False,
    help="Show what would be deleted without actually deleting.",
)
@click.option(
    "--yes",
    "-y",
    is_flag=True,
    default=False,
    help="Skip confirmation prompt.",
)
def delete_cmd(
    path: Path,
    types: tuple[str, ...],
    older_than: int | None,
    dry_run: bool,
    yes: bool,
) -> None:
    """Delete detected Python environments under PATH.

    By default, shows a confirmation prompt before deleting.
    Use --dry-run to preview which environments would be removed.
    """
    console = Console()

    scanner = Scanner(types=set(types) if types else None)
    envs = scanner.scan(path)
    envs = _filter_envs(envs, types or None, older_than)

    if not envs:
        console.print("[yellow]No environments found matching the criteria.[/yellow]")
        return

    total_bytes = sum(e.size_bytes for e in envs)

    console.print(
        f"\nFound [bold]{len(envs)}[/bold] environment(s) — "
        f"[bold]{format_size(total_bytes)}[/bold] total\n"
    )
    for env in envs:
        flag = "[dim][dry-run][/dim] " if dry_run else ""
        console.print(
            f"  {flag}[red]{env.type}[/red]  {env.name}  {env.size_human}  {env.path}"
        )

    if dry_run:
        console.print("\n[bold yellow]Dry run — nothing deleted.[/bold yellow]")
        return

    if not yes:
        click.confirm(
            f"\nDelete {len(envs)} environment(s)? This cannot be undone.",
            abort=True,
        )

    cleaner = Cleaner(dry_run=False)
    freed = 0
    errors = 0

    for env in envs:
        try:
            freed += cleaner.delete(env)
            console.print(f"  [green]✓[/green] Deleted {env.name} ({env.size_human})")
        except CleanerError as exc:
            console.print(f"  [red]✗[/red] {env.name}: {exc}")
            errors += 1

    console.print(
        f"\n[bold green]Done.[/bold green] "
        f"Freed [bold]{format_size(freed)}[/bold]"
        + (f" — [red]{errors} error(s)[/red]" if errors else "")
    )

    if errors:
        sys.exit(1)
