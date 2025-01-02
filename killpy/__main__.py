import os
from textual.app import App, ComposeResult
from textual.widgets import DataTable, Header
import time
import shutil
from pathlib import Path


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
        last_modified = int(
            round((time.time() - dir_path.stat().st_mtime) / (24 * 3600))
        )
        size = format_size(get_total_size(dir_path))
        venvs.append((dir_path, last_modified, size))

    return venvs


class TableApp(App):

    deleted_cells = []

    def compose(self) -> ComposeResult:
        yield Header()
        yield DataTable()

    def on_mount(self) -> None:
        self.title = """KillPy"""

        current_directory = Path.cwd()

        venvs = find_venvs(current_directory)
        table = self.query_one(DataTable)
        table.focus()
        table.add_columns("Path", "Last Modified", "Size")
        for venv in venvs:
            table.add_row(*venv)
        table.cursor_type = "row"
        table.zebra_stripes = True

    def on_key(self, event):
        if event.key == "enter":
            table = self.query_one(DataTable)
            cursor_cell = table.cursor_coordinate
            if cursor_cell:
                if cursor_cell in self.deleted_cells:
                    return event
                row_data = table.get_row_at(cursor_cell.row)
                path = row_data[0]
                shutil.rmtree(path)
                table.update_cell_at(cursor_cell, f"DELETED {row_data[0]}")
                self.deleted_cells.append(cursor_cell)
            self.bell()
        return event


def main():
    app = TableApp()
    app.run()


if __name__ == "__main__":
    main()
