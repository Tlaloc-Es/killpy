import asyncio
from enum import Enum
from pathlib import Path

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.color import Gradient
from textual.coordinate import Coordinate
from textual.widgets import (
    DataTable,
    Footer,
    Header,
    Label,
    ProgressBar,
    Static,
    TabbedContent,
    TabPane,
)

from killpy import __version__
from killpy.cleaners import remove_pycache
from killpy.files import format_size
from killpy.killers import (
    CondaKiller,
    PipxKiller,
    PoetryKiller,
    PyenvKiller,
    VenvKiller,
)


def is_venv_tab(func):
    def wrapper(self, *args, **kwargs):
        if self.query_one(TabbedContent).active == "venv-tab":
            return func(self, *args, **kwargs)

    return wrapper


def is_pipx_tab(func):
    def wrapper(self, *args, **kwargs):
        if self.query_one(TabbedContent).active == "pipx-tab":
            return func(self, *args, **kwargs)

    return wrapper


def remove_duplicates(venvs):
    seen_paths = set()
    unique_venvs = []

    for venv in venvs:
        venv_path = venv[0]
        if venv_path not in seen_paths:
            unique_venvs.append(venv)
            seen_paths.add(venv_path)

    return unique_venvs


class EnvStatus(Enum):
    DELETED = "DELETED"
    MARKED_TO_DELETE = "MARKED TO DELETE"


class TableApp(App):
    deleted_cells: Coordinate = []
    bytes_release: int = 0

    killers = {
        "conda_killer": CondaKiller(),
        "pipx_killer": PipxKiller(),
        "poetry_killer": PoetryKiller(Path.cwd()),
        "venv_killer": VenvKiller(Path.cwd()),
        "pyenv_killer": PyenvKiller(Path.cwd()),
    }

    BINDINGS = [
        Binding(key="ctrl+q", action="quit", description="Exit"),
        Binding(
            key="d",
            action="mark_for_delete",
            description="Mark for deletion",
            show=True,
        ),
        Binding(
            key="ctrl+d",
            action="confirm_delete",
            description="Delete marked",
            show=True,
        ),
        Binding(
            key="shift+delete",
            action="delete_now",
            description="Delete immediately",
            show=True,
        ),
        Binding(
            key="p",
            action="clean_pycache",
            description="Clean __pycache__ dirs",
            show=True,
        ),
        Binding(
            key="u",
            action="uninstall_pipx",
            description="Uninstall pipx packages",
            show=True,
        ),
    ]

    CSS = """
    #banner {
        color: white;
        border: heavy green;
    }

    TabbedContent #--content-tab-venv-tab {
        color: green;
    }

    TabbedContent #--content-tab-pipx-tab {
        color: yellow;
    }
    """

    def compose(self) -> ComposeResult:
        yield Header()
        banner = Static(
            f"""
█  ▄ ▄ █ █ ▄▄▄▄  ▄   ▄              ____
█▄▀  ▄ █ █ █   █ █   █           .'`_ o `;__,
█ ▀▄ █ █ █ █▄▄▄▀  ▀▀▀█ .       .'.'` '---'  ' A tool to delete
█  █ █ █ █ █     ▄   █  .`-...-'.' .venv, Conda, Poetry environments
           ▀      ▀▀▀    `-...-'and clean up __pycache__ and temp files.

                                           Version {__version__}
        """,
            id="banner",
        )
        yield banner
        yield Label("Searching for virtual environments...")

        gradient = Gradient.from_colors(
            "#881177",
            "#aa3355",
            "#cc6666",
            "#ee9944",
            "#eedd00",
            "#99dd55",
            "#44dd88",
            "#22ccbb",
            "#00bbcc",
            "#0099cc",
            "#3366bb",
            "#663399",
        )
        yield ProgressBar(total=100, gradient=gradient, show_eta=False)

        with TabbedContent():
            with TabPane("Virtual Env", id="venv-tab"):
                yield DataTable(id="venv-table")
            with TabPane("Pipx", id="pipx-tab"):
                yield DataTable(id="pipx-table")

        yield Footer(show_command_palette=False)

    async def on_mount(self) -> None:
        self.title = """killpy"""
        await self.find_venvs()
        await self.find_pipx()

    def list_environments_of(self, killer: str):
        return asyncio.to_thread(self.killers[killer].list_environments)

    async def find_venvs(self):
        venvs = await asyncio.gather(
            self.list_environments_of("venv_killer"),
            self.list_environments_of("conda_killer"),
            self.list_environments_of("pyenv_killer"),
            self.list_environments_of("poetry_killer"),
        )
        venvs = [env for sublist in venvs for env in sublist]
        venvs = remove_duplicates(venvs)

        table = self.query_one("#venv-table", DataTable)
        table.focus()
        table.add_columns(
            "Path", "Type", "Last Modified", "Size", "Size (Human Readable)", "Status"
        )

        for venv in venvs:
            table.add_row(*venv)

        table.cursor_type = "row"
        table.zebra_stripes = True

        self.query_one(Label).update(f"Found {len(venvs)} .venv directories")

    async def find_pipx(self):
        venvs = await asyncio.gather(self.list_environments_of("pipx_killer"))

        venvs = [env for sublist in venvs for env in sublist]

        table = self.query_one("#pipx-table", DataTable)
        table.focus()
        table.add_columns("Package", "Size", "Size (Human Readable)", "Status")

        for venv in venvs:
            table.add_row(*venv)

        table.cursor_type = "row"
        table.zebra_stripes = True

        self.query_one(Label).update(f"Found {len(venvs)} .venv directories")

    async def action_clean_pycache(self):
        current_directory = Path.cwd()
        total_freed_space = await asyncio.to_thread(remove_pycache, current_directory)
        self.bytes_release += total_freed_space
        self.query_one(Label).update(f"{format_size(self.bytes_release)} deleted")
        self.bell()

    @is_venv_tab
    def action_confirm_delete(self):
        table = self.query_one("#venv-table", DataTable)
        for row_index in range(table.row_count):
            row_data = table.get_row_at(row_index)
            current_status = row_data[5]
            if current_status == EnvStatus.MARKED_TO_DELETE.value:
                cursor_cell = Coordinate(row_index, 0)
                if cursor_cell not in self.deleted_cells:
                    path = row_data[0]
                    self.bytes_release += row_data[3]
                    env_type = row_data[1]
                    self.delete_environment(path, env_type)
                    table.update_cell_at((row_index, 5), EnvStatus.DELETED.value)
                    self.deleted_cells.append(cursor_cell)
        self.query_one(Label).update(f"{format_size(self.bytes_release)} deleted")
        self.bell()

    @is_venv_tab
    def action_mark_for_delete(self):
        table = self.query_one("#venv-table", DataTable)

        cursor_cell = table.cursor_coordinate
        if cursor_cell:
            row_data = table.get_row_at(cursor_cell.row)
            current_status = row_data[5]
            if current_status == EnvStatus.DELETED.value:
                return
            elif current_status == EnvStatus.MARKED_TO_DELETE.value:
                table.update_cell_at((cursor_cell.row, 5), "")
            else:
                table.update_cell_at(
                    (cursor_cell.row, 5), EnvStatus.MARKED_TO_DELETE.value
                )

    @is_venv_tab
    def action_delete_now(self):
        table = self.query_one("#venv-table", DataTable)
        cursor_cell = table.cursor_coordinate
        if cursor_cell:
            if cursor_cell in self.deleted_cells:
                return
            row_data = table.get_row_at(cursor_cell.row)
            path = row_data[0]
            self.bytes_release += row_data[3]
            env_type = row_data[1]
            self.delete_environment(path, env_type)
            table.update_cell_at((cursor_cell.row, 5), EnvStatus.DELETED.value)
            self.query_one(Label).update(f"{format_size(self.bytes_release)} deleted")
            self.deleted_cells.append(cursor_cell)
        self.bell()

    @is_venv_tab
    def delete_environment(self, path, env_type):
        if env_type in {".venv", "pyvenv.cfg", "poetry"}:
            self.killers["venv_killer"].remove_environment(path)
        else:
            self.killers["conda_killer"].remove_environment(path)

    @is_pipx_tab
    def action_uninstall_pipx(self):
        table = self.query_one("#pipx-table", DataTable)
        cursor_cell = table.cursor_coordinate
        if cursor_cell:
            if cursor_cell in self.deleted_cells:
                return
            row_data = table.get_row_at(cursor_cell.row)
            package = row_data[0]
            size = row_data[1]

            self.killers["pipx_killer"].remove_environment(package)

            table.update_cell_at((cursor_cell.row, 3), EnvStatus.DELETED.value)
            self.deleted_cells.append(cursor_cell)
            self.bytes_release += size
            self.query_one(Label).update(f"{format_size(self.bytes_release)} deleted")

        self.bell()
