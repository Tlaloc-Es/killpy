"""``killpy clean`` – remove ``__pycache__`` directories under a path."""

from __future__ import annotations

from pathlib import Path

import click

from killpy.cleaners import remove_pycache
from killpy.files import format_size


@click.command("clean")
@click.option(
    "--path",
    default=Path.cwd,
    type=click.Path(path_type=Path, exists=True, file_okay=False, dir_okay=True),
    help="Path to the directory to clean",
)
def clean_cmd(path: Path) -> None:
    """Remove all ``__pycache__`` directories under PATH and report freed space."""
    click.echo(f"Cleaning {path}…")
    total_freed_space = remove_pycache(path)
    click.echo(f"{format_size(total_freed_space)} freed")
