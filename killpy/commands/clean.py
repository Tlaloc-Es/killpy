import logging
from pathlib import Path

import click

from killpy.cleaners import remove_pycache
from killpy.files import format_size


@click.command()
@click.option("--path", default=Path.cwd(), help="Path to the directory to clean")
def clean(path):
    path = Path(path)
    logging.info(f"Executing the clean command in {path}")
    total_freed_space = remove_pycache(path)
    logging.info(f"{format_size(total_freed_space)} deleted")
