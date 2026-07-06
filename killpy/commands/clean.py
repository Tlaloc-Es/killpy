from pathlib import Path

import click

from killpy.cleaners import remove_pycache
from killpy.files import format_size


@click.command()
@click.option(
    "--path",
    default=Path.cwd,
    type=click.Path(path_type=Path, exists=True, file_okay=False, dir_okay=True),
    help="Path to the directory to clean",
)
def clean(path: Path):
    click.echo(f"Cleaning {path}…")
    total_freed_space = remove_pycache(path)
    click.echo(f"{format_size(total_freed_space)} freed")
