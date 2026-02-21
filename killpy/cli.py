import asyncio
from datetime import datetime
from enum import Enum
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import Any, TypedDict

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal
from textual.widgets import (
    DataTable,
    Footer,
    Header,
    Label,
    LoadingIndicator,
    Static,
    TabbedContent,
    TabPane,
)

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


def shorten_path_for_table(path_value, max_parts: int = 2) -> str:
    path_text = str(path_value)
    if "/" not in path_text and "\\" not in path_text:
        return path_text

    normalized_path = path_text.replace("\\", "/").strip("/")
    parts = [part for part in normalized_path.split("/") if part]
    if len(parts) <= max_parts:
        return path_text

    return ".../" + "/".join(parts[-max_parts:])


class EnvStatus(Enum):
    DELETED = "DELETED"
    MARKED_TO_DELETE = "MARKED TO DELETE"


class VenvRow(TypedDict):
    path: str
    type: str
    last_modified: str
    size: int
    size_human: str
    status: str


class PipxRow(TypedDict):
    package: str
    size: int
    size_human: str
    status: str


class TableApp(App):
    VENV_HEADERS = [
        "Path",
        "Type",
        "Last Modified",
        "Size",
        "Size (Human Readable)",
        "Status",
    ]
    PIPX_HEADERS = ["Package", "Size", "Size (Human Readable)", "Status"]
    VENV_COL_PATH = 0
    VENV_COL_TYPE = 1
    VENV_COL_LAST_MODIFIED = 2
    VENV_COL_SIZE = 3
    VENV_COL_SIZE_HUMAN = 4
    VENV_COL_STATUS = 5

    PIPX_COL_PACKAGE = 0
    PIPX_COL_SIZE = 1
    PIPX_COL_SIZE_HUMAN = 2
    PIPX_COL_STATUS = 3

    def __init__(self, root_dir: Path | None = None, *args: Any, **kwargs: Any):
        super().__init__(*args, **kwargs)
        self.app_version = self.get_app_version()
        self.root_dir = root_dir or Path.cwd()
        self.venv_rows: list[VenvRow] = []
        self.pipx_rows: list[PipxRow] = []
        self.sort_state: dict[str, tuple[int, bool]] = {}
        self.bytes_release: int = 0
        self.killers = {
            "conda_killer": CondaKiller(),
            "pipx_killer": PipxKiller(),
            "poetry_killer": PoetryKiller(self.root_dir),
            "venv_killer": VenvKiller(self.root_dir),
            "pyenv_killer": PyenvKiller(self.root_dir),
        }

    @staticmethod
    def get_app_version() -> str:
        try:
            return version("killpy")
        except PackageNotFoundError:
            return "dev"

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

    #loading-row {
        height: 1;
    }

    #scan-loading {
        width: 3;
        height: 1;
    }

    #status-label {
        height: 1;
    }

    #selected-path-label {
        height: 1;
        color: $text-muted;
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
                            v{self.app_version}
        """,
            id="banner",
        )
        yield banner
        with Horizontal(id="loading-row"):
            yield LoadingIndicator(id="scan-loading")
            yield Label("Preparing scan...", id="status-label")
        yield Label("", id="selected-path-label")

        with TabbedContent():
            with TabPane("Virtual Env", id="venv-tab"):
                yield DataTable(id="venv-table")
            with TabPane("Pipx", id="pipx-tab"):
                yield DataTable(id="pipx-table")

        yield Footer(show_command_palette=False)

    async def on_mount(self) -> None:
        self.title = """killpy"""

    async def on_ready(self) -> None:
        self.run_worker(self.load_initial_data(), exclusive=True)

    def setup_tables(self) -> None:
        venv_table = self.query_one("#venv-table", DataTable)
        if not venv_table.columns:
            venv_table.add_columns(*self.get_headers_for_table("venv-table"))
        venv_table.cursor_type = "row"
        venv_table.zebra_stripes = True

        pipx_table = self.query_one("#pipx-table", DataTable)
        if not pipx_table.columns:
            pipx_table.add_columns(*self.get_headers_for_table("pipx-table"))
        pipx_table.cursor_type = "row"
        pipx_table.zebra_stripes = True

        venv_table.focus()

    def add_venv_environment(self, environment: tuple[Any, ...]) -> None:
        self.venv_rows.append(
            {
                "path": str(environment[0]),
                "type": environment[1],
                "last_modified": environment[2],
                "size": environment[3],
                "size_human": environment[4],
                "status": "",
            }
        )

        table = self.query_one("#venv-table", DataTable)
        row = self.venv_rows[-1]
        table.add_row(
            shorten_path_for_table(row["path"]),
            row["type"],
            row["last_modified"],
            row["size"],
            row["size_human"],
            row["status"],
        )

    def add_pipx_environment(self, environment: tuple[Any, ...]) -> None:
        self.pipx_rows.append(
            {
                "package": environment[0],
                "size": environment[1],
                "size_human": environment[2],
                "status": "",
            }
        )

        table = self.query_one("#pipx-table", DataTable)
        row = self.pipx_rows[-1]
        table.add_row(row["package"], row["size"], row["size_human"], row["status"])

    def render_venv_table(self) -> None:
        table = self.query_one("#venv-table", DataTable)
        table.clear(columns=True)
        table.add_columns(*self.get_headers_for_table("venv-table"))
        for row in self.venv_rows:
            table.add_row(
                shorten_path_for_table(row["path"]),
                row["type"],
                row["last_modified"],
                row["size"],
                row["size_human"],
                row["status"],
            )

    def render_pipx_table(self) -> None:
        table = self.query_one("#pipx-table", DataTable)
        table.clear(columns=True)
        table.add_columns(*self.get_headers_for_table("pipx-table"))
        for row in self.pipx_rows:
            table.add_row(row["package"], row["size"], row["size_human"], row["status"])

    def get_headers_for_table(self, table_id: str) -> list[str]:
        base_headers = (
            self.VENV_HEADERS if table_id == "venv-table" else self.PIPX_HEADERS
        )
        sort_info = self.sort_state.get(table_id)
        if not sort_info:
            return list(base_headers)

        sort_index, is_descending = sort_info
        arrow = "↓" if is_descending else "↑"
        headers = list(base_headers)
        if 0 <= sort_index < len(headers):
            headers[sort_index] = f"{headers[sort_index]} {arrow}"
        return headers

    def sort_venv_rows(self, column_index: int, reverse: bool) -> None:
        def date_key(value: str):
            try:
                return datetime.strptime(value, "%d/%m/%Y")
            except ValueError:
                return datetime.min

        if column_index == self.VENV_COL_TYPE:
            self.venv_rows.sort(key=lambda row: row["type"].lower(), reverse=reverse)
        elif column_index == self.VENV_COL_LAST_MODIFIED:
            self.venv_rows.sort(
                key=lambda row: date_key(row["last_modified"]), reverse=reverse
            )
        elif column_index == self.VENV_COL_SIZE:
            self.venv_rows.sort(key=lambda row: row["size"], reverse=reverse)
        elif column_index == self.VENV_COL_SIZE_HUMAN:
            self.venv_rows.sort(
                key=lambda row: row["size_human"].lower(), reverse=reverse
            )
        elif column_index == self.VENV_COL_STATUS:
            self.venv_rows.sort(key=lambda row: row["status"].lower(), reverse=reverse)
        else:
            self.venv_rows.sort(key=lambda row: row["path"].lower(), reverse=reverse)
        self.render_venv_table()

    def sort_pipx_rows(self, column_index: int, reverse: bool) -> None:
        if column_index == self.PIPX_COL_SIZE:
            self.pipx_rows.sort(key=lambda row: row["size"], reverse=reverse)
        elif column_index == self.PIPX_COL_SIZE_HUMAN:
            self.pipx_rows.sort(
                key=lambda row: row["size_human"].lower(), reverse=reverse
            )
        elif column_index == self.PIPX_COL_STATUS:
            self.pipx_rows.sort(key=lambda row: row["status"].lower(), reverse=reverse)
        else:
            self.pipx_rows.sort(key=lambda row: row["package"].lower(), reverse=reverse)
        self.render_pipx_table()

    def on_data_table_header_selected(self, event: DataTable.HeaderSelected) -> None:
        table_id = event.data_table.id
        if table_id not in {"venv-table", "pipx-table"}:
            return

        column_index = getattr(event, "column_index", None)
        if column_index is None and hasattr(event, "column"):
            column_index = getattr(event.column, "index", None)
        if column_index is None:
            column_index = 0
        previous_sort = self.sort_state.get(table_id)
        reverse = False
        if previous_sort and previous_sort[0] == column_index:
            reverse = not previous_sort[1]

        self.sort_state[table_id] = (column_index, reverse)
        if table_id == "venv-table":
            self.sort_venv_rows(column_index, reverse)
        else:
            self.sort_pipx_rows(column_index, reverse)

    async def fetch_killer_data(self, killer: str):
        return killer, await self.list_environments_of(killer)

    async def load_initial_data(self) -> None:
        status_label = self.query_one("#status-label", Label)
        loading = self.query_one("#scan-loading", LoadingIndicator)
        self.setup_tables()

        status_label.update("Scanning environments...")
        loading.display = True

        killer_names = [
            "venv_killer",
            "conda_killer",
            "pyenv_killer",
            "poetry_killer",
            "pipx_killer",
        ]
        total_tasks = len(killer_names)
        completed_tasks = 0
        venv_count = 0
        pipx_count = 0
        seen_venv_paths = set()

        tasks = [
            asyncio.create_task(self.fetch_killer_data(name)) for name in killer_names
        ]
        for task in asyncio.as_completed(tasks):
            killer, environments = await task

            if killer == "pipx_killer":
                for environment in environments:
                    self.add_pipx_environment(environment)
                    pipx_count += 1
            else:
                for environment in environments:
                    environment_path = environment[0]
                    if environment_path in seen_venv_paths:
                        continue
                    seen_venv_paths.add(environment_path)
                    self.add_venv_environment(environment)
                    venv_count += 1

            completed_tasks += 1
            status_label.update(
                f"Scanning ({completed_tasks}/{total_tasks})... "
                f"{venv_count} virtual environments, {pipx_count} pipx packages"
            )

        loading.display = False
        status_label.update(
            f"Found {venv_count} virtual environments and {pipx_count} pipx packages"
        )

    def list_environments_of(self, killer: str):
        return asyncio.to_thread(self.killers[killer].list_environments)

    async def action_clean_pycache(self):
        total_freed_space = await asyncio.to_thread(remove_pycache, self.root_dir)
        self.bytes_release += total_freed_space
        self.query_one("#status-label", Label).update(
            f"{format_size(self.bytes_release)} deleted"
        )
        self.bell()

    def on_data_table_row_highlighted(self, event: DataTable.RowHighlighted) -> None:
        selected_path_label = self.query_one("#selected-path-label", Label)
        if event.data_table.id != "venv-table":
            selected_path_label.update("")
            return

        row_index = event.cursor_row
        if row_index is None:
            selected_path_label.update("")
            return

        if 0 <= row_index < len(self.venv_rows):
            selected_path_label.update(f"Selected: {self.venv_rows[row_index]['path']}")

    @is_venv_tab
    def action_confirm_delete(self):
        table = self.query_one("#venv-table", DataTable)
        for row_index, row in enumerate(self.venv_rows):
            if row["status"] != EnvStatus.MARKED_TO_DELETE.value:
                continue

            self.bytes_release += int(row["size"])
            self.delete_environment(row["path"], row["type"])
            row["status"] = EnvStatus.DELETED.value
            table.update_cell_at((row_index, 5), EnvStatus.DELETED.value)

        self.query_one("#status-label", Label).update(
            f"{format_size(self.bytes_release)} deleted"
        )
        self.bell()

    @is_venv_tab
    def action_mark_for_delete(self):
        table = self.query_one("#venv-table", DataTable)

        cursor_cell = table.cursor_coordinate
        if cursor_cell:
            row = self.venv_rows[cursor_cell.row]
            current_status = row["status"]
            if current_status == EnvStatus.DELETED.value:
                return
            elif current_status == EnvStatus.MARKED_TO_DELETE.value:
                row["status"] = ""
                table.update_cell_at((cursor_cell.row, 5), "")
            else:
                row["status"] = EnvStatus.MARKED_TO_DELETE.value
                table.update_cell_at(
                    (cursor_cell.row, 5), EnvStatus.MARKED_TO_DELETE.value
                )

    @is_venv_tab
    def action_delete_now(self):
        table = self.query_one("#venv-table", DataTable)
        cursor_cell = table.cursor_coordinate
        if cursor_cell:
            row = self.venv_rows[cursor_cell.row]
            if row["status"] == EnvStatus.DELETED.value:
                return
            self.bytes_release += int(row["size"])
            self.delete_environment(row["path"], row["type"])
            row["status"] = EnvStatus.DELETED.value
            table.update_cell_at((cursor_cell.row, 5), EnvStatus.DELETED.value)
            self.query_one("#status-label", Label).update(
                f"{format_size(self.bytes_release)} deleted"
            )
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
            row = self.pipx_rows[cursor_cell.row]
            if row["status"] == EnvStatus.DELETED.value:
                return
            package = row["package"]
            size = int(row["size"])

            self.killers["pipx_killer"].remove_environment(package)

            row["status"] = EnvStatus.DELETED.value
            table.update_cell_at((cursor_cell.row, 3), EnvStatus.DELETED.value)
            self.bytes_release += size
            self.query_one("#status-label", Label).update(
                f"{format_size(self.bytes_release)} deleted"
            )

        self.bell()
