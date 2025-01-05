import asyncio
import shutil
from enum import Enum
from pathlib import Path

from envs_handler import (
    find_venvs,
    find_venvs_with_pyvenv,
    format_size,
    list_conda_environments,
    remove_conda_env,
    remove_duplicates,
)
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.coordinate import Coordinate
from textual.widgets import DataTable, Footer, Header, Label, Static


class EnvStatus(Enum):
    DELETED = "DELETED"
    MARKED_TO_DELETE = "MARKED TO DELETE"


class TableApp(App):
    deleted_cells: Coordinate = []
    bytes_release: int = 0

    BINDINGS = [
        Binding(key="ctrl+q", action="quit", description="Quit the app"),
        Binding(
            key="d",
            action="mark_for_delete",
            description="Mark .venv for deletion",
            show=True,
        ),
        Binding(
            key="ctrl+d",
            action="confirm_delete",
            description="Confirm deletion of marked .venv",
            show=True,
        ),
        Binding(
            key="shift+delete",
            action="delete_now",
            description="Delete the selected .venv immediately",
            show=True,
        ),
    ]

    CSS = """
    #banner {
        color: white;
        border: heavy green;
    }
    """

    def compose(self) -> ComposeResult:
        yield Header()
        banner = Static(
            """
█  ▄ ▄ █ █ ▄▄▄▄  ▄   ▄              ____
█▄▀  ▄ █ █ █   █ █   █           .'`_ o `;__,
█ ▀▄ █ █ █ █▄▄▄▀  ▀▀▀█ .       .'.'` '---'  '
█  █ █ █ █ █     ▄   █  .`-...-'.'
           ▀      ▀▀▀    `-...-' A tool to delete .venv directories and Conda envs
        """,
            id="banner",
        )
        yield banner
        yield Label("Searching for virtual environments...")
        yield DataTable()
        yield Footer()

    async def on_mount(self) -> None:
        self.title = """killpy"""
        await self.find_venvs()

    async def find_venvs(self):
        current_directory = Path.cwd()

        venvs = await asyncio.gather(
            asyncio.to_thread(find_venvs, current_directory),
            asyncio.to_thread(list_conda_environments),
            asyncio.to_thread(find_venvs_with_pyvenv, current_directory),
        )
        venvs = [env for sublist in venvs for env in sublist]
        venvs = remove_duplicates(venvs)

        table = self.query_one(DataTable)
        table.focus()
        table.add_columns(
            "Path", "Type", "Last Modified", "Size", "Size (Human Readable)", "Status"
        )

        for venv in venvs:
            table.add_row(*venv)

        table.cursor_type = "row"
        table.zebra_stripes = True

        self.query_one(Label).update(f"Found {len(venvs)} .venv directories")

    def action_confirm_delete(self):
        table = self.query_one(DataTable)
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

    def action_mark_for_delete(self):
        table = self.query_one(DataTable)
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

    def action_delete_now(self):
        table = self.query_one(DataTable)
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

    def delete_environment(self, path, env_type):
        if env_type in {".venv", "pyvenv.cfg"}:
            shutil.rmtree(path)
        else:
            remove_conda_env(path)


def main():
    app = TableApp()
    app.run()


if __name__ == "__main__":
    main()
