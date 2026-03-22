"""``killpy stats`` – aggregate disk usage grouped by environment type."""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

import click
from rich.console import Console
from rich.table import Table

from killpy.files import format_size
from killpy.scanner import Scanner


@click.command("stats")
@click.option(
    "--path",
    default=Path.cwd,
    type=click.Path(path_type=Path, exists=True, file_okay=False, dir_okay=True),
    help="Root directory to scan.",
)
@click.option(
    "--json",
    "as_json",
    is_flag=True,
    default=False,
    help="Output as JSON.",
)
def stats_cmd(path: Path, as_json: bool) -> None:
    """Show disk-usage statistics grouped by environment type."""
    scanner = Scanner()
    envs = scanner.scan(path)

    # Aggregate by type
    by_type: dict[str, dict] = defaultdict(lambda: {"count": 0, "size_bytes": 0})
    for env in envs:
        by_type[env.type]["count"] += 1
        by_type[env.type]["size_bytes"] += env.size_bytes

    total_bytes = sum(e.size_bytes for e in envs)
    total_count = len(envs)

    if as_json:
        output = {
            "total_count": total_count,
            "total_size_bytes": total_bytes,
            "total_size_human": format_size(total_bytes),
            "by_type": {
                t: {
                    "count": data["count"],
                    "size_bytes": data["size_bytes"],
                    "size_human": format_size(data["size_bytes"]),
                }
                for t, data in sorted(by_type.items())
            },
        }
        click.echo(json.dumps(output, indent=2))
        return

    if not envs:
        click.echo("No environments found.")
        return

    console = Console()
    table = Table(show_header=True, header_style="bold cyan", title="Environment stats")
    table.add_column("Type", style="dim", min_width=14)
    table.add_column("Count", justify="right", min_width=7)
    table.add_column("Total size", justify="right", min_width=12)
    table.add_column("Avg size", justify="right", min_width=10)

    for env_type, data in sorted(by_type.items(), key=lambda x: -x[1]["size_bytes"]):
        avg = data["size_bytes"] // data["count"] if data["count"] else 0
        table.add_row(
            env_type,
            str(data["count"]),
            format_size(data["size_bytes"]),
            format_size(avg),
        )

    console.print(table)
    console.print(
        f"\nTotal: [bold]{total_count}[/bold] environment(s) — "
        f"[bold]{format_size(total_bytes)}[/bold]"
    )
