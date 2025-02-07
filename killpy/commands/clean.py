from pathlib import Path

import click

from killpy.cleaners import remove_pycache


@click.command()
@click.option("--path", default=Path.cwd(), help="Path to the directory to clean")
def clean(path):
    path = Path(path)
    click.echo(f"Executing the clean command in {path}")
    remove_pycache(path)
