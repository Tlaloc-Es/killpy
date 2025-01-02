import os
from textual.app import App, ComposeResult
from textual.widgets import DataTable, Header
import time


def get_folder_size(folder_path):
    total_size = 0
    for dirpath, dirnames, filenames in os.walk(folder_path):
        for filename in filenames:
            file_path = os.path.join(dirpath, filename)
            total_size += os.path.getsize(file_path)
    return total_size


def format_size(size_in_bytes):
    if size_in_bytes >= 1 << 30:
        return f"{size_in_bytes / (1 << 30):.2f} GB"
    elif size_in_bytes >= 1 << 20:
        return f"{size_in_bytes / (1 << 20):.2f} MB"
    elif size_in_bytes >= 1 << 10:
        return f"{size_in_bytes / (1 << 10):.2f} KB"
    else:
        return f"{size_in_bytes} bytes"


def find_venvs(base_directory="."):
    venvs = []

    for root, dirs, files in os.walk(base_directory):
        for dir_name in dirs:
            if dir_name.startswith(".venv"):
                venv_path = os.path.join(root, dir_name)
                last_modified = int(
                    round((time.time() - os.path.getmtime(venv_path)) / (24 * 3600))
                )
                size = format_size(get_folder_size(venv_path))
                venvs.append((venv_path, last_modified, size))

    return venvs


class TableApp(App):
    def compose(self) -> ComposeResult:
        yield Header()
        yield DataTable()

    def on_mount(self) -> None:
        self.title = """KillPy"""

        current_directory = os.getcwd()

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
                row_data = table.get_row_at(cursor_cell.row)

                table.update_cell_at(cursor_cell, f"DELETED {row_data[0]}")

            self.bell()
        return event


def main():
    app = TableApp()
    app.run()


if __name__ == "__main__":
    main()
