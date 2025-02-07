import click

from killpy.cli import TableApp
from killpy.commands.clean import clean


@click.group(invoke_without_command=True)
@click.pass_context
def cli(ctx):
    if not ctx.invoked_subcommand:
        app = TableApp()
        app.run()


cli.add_command(clean)


if __name__ == "__main__":
    cli()
