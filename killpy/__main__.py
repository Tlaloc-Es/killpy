import shutil
import subprocess
from datetime import datetime
from pathlib import Path

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.coordinate import Coordinate
from textual.widgets import DataTable, Footer, Header, Label, Static


def get_total_size(path: Path) -> int:
    total_size = sum(f.stat().st_size for f in path.rglob("*") if f.is_file())
    return total_size


def format_size(size_in_bytes: int):
    if size_in_bytes >= 1 << 30:
        return f"{size_in_bytes / (1 << 30):.2f} GB"
    elif size_in_bytes >= 1 << 20:
        return f"{size_in_bytes / (1 << 20):.2f} MB"
    elif size_in_bytes >= 1 << 10:
        return f"{size_in_bytes / (1 << 10):.2f} KB"
    else:
        return f"{size_in_bytes} bytes"


def find_venvs(base_directory: Path):
    venvs = []
    for dir_path in base_directory.rglob(".venv"):
        last_modified_timestamp = dir_path.stat().st_mtime
        last_modified = datetime.fromtimestamp(last_modified_timestamp).strftime(
            "%d/%m/%Y"
        )
        size = get_total_size(dir_path)
        size_to_show = format_size(size)
        venvs.append((dir_path, ".venv", last_modified, size, size_to_show))
        venvs.sort(key=lambda x: x[2], reverse=True)

    return venvs


def remove_conda_env(env_name):
    try:
        subprocess.run(
            ["conda", "env", "remove", "-n", env_name],
            check=True,
        )
    except subprocess.CalledProcessError as e:
        print(f"Error: {e}")


def list_conda_environments():
    try:
        result = subprocess.run(
            ["conda", "env", "list"],
            capture_output=True,
            text=True,
            check=True,
        )

        venvs = []
        for line in result.stdout.splitlines():
            if line.strip() and not line.startswith("#"):
                env_info = line.strip().split()
                env_name = env_info[0]

                if "*" in env_info:
                    continue

                dir_path = Path(env_info[1])
                last_modified_timestamp = dir_path.stat().st_mtime
                last_modified = datetime.fromtimestamp(
                    last_modified_timestamp
                ).strftime("%d/%m/%Y")

                size = get_total_size(dir_path)
                size_to_show = format_size(size)
                venvs.append((env_name, "Conda", last_modified, size, size_to_show))

        venvs.sort(key=lambda x: x[3], reverse=True)
        return venvs

    except subprocess.CalledProcessError as e:
        print(f"Error: {e}")
        return []


class TableApp(App):
    deleted_cells: Coordinate = []
    bytes_release: int = 0
    BINDINGS = [
        Binding(key="ctrl+q", action="quit", description="Quit the app"),
        Binding(
            key="ctrl+m",
            action="enter",
            description="Delete the .venv selected",
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
▗▖ ▗▖▄ █ █ ▗▄▄▖ ▄   ▄              ____
▐▌▗▞▘▄ █ █ ▐▌ ▐▌█   █           .'`_ o `;__,
▐▛▚▖ █ █ █ ▐▛▀▘  ▀▀▀█ .       .'.'` '---'  '
▐▌ ▐▌█ █ █ ▐▌   ▄   █  .`-...-'.'
                 ▀▀▀    `-...-' A tool to delete .venv directories
        """,
            id="banner",
        )
        yield banner
        yield Label("Finding .venv directories...")
        yield DataTable()
        yield Footer()

    def on_mount(self) -> None:
        self.title = """KillPy"""

        current_directory = Path.cwd()

        venvs = find_venvs(current_directory)
        venvs += list_conda_environments()
        table = self.query_one(DataTable)
        table.focus()
        table.add_columns(
            "Path", "Type", "Last Modified", "Size", "Size (Human Readable)"
        )
        for venv in venvs:
            table.add_row(*venv)
        table.cursor_type = "row"
        table.zebra_stripes = True
        self.query_one(Label).update(f"Found {len(venvs)} .venv directories")

    def on_key(self, event):
        if event.key == "enter":
            table = self.query_one(DataTable)
            cursor_cell = table.cursor_coordinate
            if cursor_cell:
                if cursor_cell in self.deleted_cells:
                    return event
                row_data = table.get_row_at(cursor_cell.row)
                path = row_data[0]
                self.bytes_release += row_data[3]
                env_type = row_data[1]
                if env_type == ".venv":
                    shutil.rmtree(path)
                else:
                    remove_conda_env(path)
                table.update_cell_at(cursor_cell, f"DELETED {path}")
                self.query_one(Label).update(
                    f"{format_size(self.bytes_release)} deleted"
                )
                self.deleted_cells.append(cursor_cell)
            self.bell()
        return event


def main():
    app = TableApp()
    app.run()


if __name__ == "__main__":
    main()
