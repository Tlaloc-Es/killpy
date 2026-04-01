from pathlib import Path

import click
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.prompt import Confirm

from killpy.cleaner import Cleaner
from killpy.cli import TableApp
from killpy.commands.clean import clean
from killpy.commands.delete import delete_cmd
from killpy.commands.list import list_cmd
from killpy.commands.stats import stats_cmd
from killpy.files import format_size
from killpy.scanner import Scanner


def _run_delete_all(path: Path, excluded: set[str], yes: bool) -> None:
    """Scan and delete all discovered environments without launching the TUI."""
    console = Console()
    scanner = Scanner(excluded=excluded)
    cleaner = Cleaner()

    with Progress(
        SpinnerColumn(),
        TextColumn("[bold cyan]Scanning…"),
        console=console,
        transient=True,
    ):
        envs = scanner.scan(path)

    if not envs:
        console.print("[yellow]No environments found.[/yellow]")
        return

    total_size = sum(e.size_bytes for e in envs)
    console.print(
        f"Found [bold]{len(envs)}[/bold] environment(s) totalling "
        f"[bold red]{format_size(total_size)}[/bold red]."
    )
    for env in envs:
        console.print(f"  [dim]{env.path}[/dim]  [cyan]{env.size_human}[/cyan]")

    if not yes:
        if not Confirm.ask(
            f"\nDelete all [bold]{len(envs)}[/bold] environments?", default=False
        ):
            console.print("Aborted.")
            return

    deleted = 0
    freed = 0
    for env in envs:
        size = env.size_bytes
        if cleaner.delete(env):
            freed += size
            deleted += 1
        else:
            console.print(f"[red]Failed to delete:[/red] {env.path}")

    console.print(
        f"\n[bold green]Done.[/bold green] Deleted {deleted}/{len(envs)} environment(s), "  # noqa: E501
        f"freed [bold]{format_size(freed)}[/bold]."
    )


@click.group(invoke_without_command=True)
@click.option(
    "--path",
    default=Path.cwd,
    type=click.Path(path_type=Path, exists=True, file_okay=False, dir_okay=True),
    help="Path to scan for virtual environments",
)
@click.option(
    "--exclude",
    "-E",
    default="",
    type=str,
    help='Comma-separated path patterns to exclude, e.g. "backups,legacy".',
)
@click.option(
    "--delete-all",
    "-D",
    is_flag=True,
    default=False,
    help="Scan and delete ALL found environments without launching the TUI.",
)
@click.option(
    "--yes",
    "-y",
    is_flag=True,
    default=False,
    help="Skip the confirmation prompt (use together with --delete-all).",
)
@click.pass_context
def cli(ctx, path: Path, exclude: str, delete_all: bool, yes: bool):
    excluded = (
        {p.strip() for p in exclude.split(",") if p.strip()} if exclude else set()
    )
    if not ctx.invoked_subcommand:
        if delete_all:
            _run_delete_all(path, excluded, yes)
        else:
            app = TableApp(root_dir=path, excluded=excluded)
            app.run()


cli.add_command(clean)
cli.add_command(list_cmd, name="list")
cli.add_command(delete_cmd, name="delete")
cli.add_command(stats_cmd, name="stats")


if __name__ == "__main__":
    cli()
