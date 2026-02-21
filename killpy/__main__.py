from pathlib import Path

import click

from killpy.cli import TableApp
from killpy.commands.clean import clean


@click.group(invoke_without_command=True)
@click.option(
    "--path",
    default=Path.cwd,
    type=click.Path(path_type=Path, exists=True, file_okay=False, dir_okay=True),
    help="Path to scan for virtual environments",
)
@click.pass_context
def cli(ctx, path: Path):
    if not ctx.invoked_subcommand:
        app = TableApp(root_dir=path)
        app.run()


cli.add_command(clean)


if __name__ == "__main__":
    cli()
