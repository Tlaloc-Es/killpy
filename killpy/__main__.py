from pathlib import Path

import click

from killpy.cli import TableApp
from killpy.commands.clean import clean
from killpy.commands.delete import delete_cmd
from killpy.commands.list import list_cmd
from killpy.commands.stats import stats_cmd


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
cli.add_command(list_cmd, name="list")
cli.add_command(delete_cmd, name="delete")
cli.add_command(stats_cmd, name="stats")


if __name__ == "__main__":
    cli()
