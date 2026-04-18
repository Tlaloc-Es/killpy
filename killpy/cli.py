import asyncio
import re
import subprocess
import sys
from datetime import datetime
from enum import Enum
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import Any, TypedDict

from rich.text import Text
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.widgets import (
    DataTable,
    Footer,
    Header,
    Input,
    Label,
    Static,
    TabbedContent,
    TabPane,
)

from killpy.cleaner import Cleaner, CleanerError
from killpy.cleaners import remove_pycache
from killpy.files import format_size
from killpy.intelligence import SuggestionEngine, score_all
from killpy.models import Environment
from killpy.scanner import Scanner

_HEALTH_STYLES: dict[str, tuple[str, str]] = {
    "HIGH": ("HIGH", "bold red"),
    "MEDIUM": ("MED", "bold yellow"),
    "LOW": ("LOW", "bold green"),
}


def _health_text(category: str) -> Text | str:
    if category in _HEALTH_STYLES:
        label, style = _HEALTH_STYLES[category]
        return Text(label, style=style)
    return ""


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
    health: str
    status: str
    environment: Environment


class PipxRow(TypedDict):
    package: str
    size: int
    size_human: str
    status: str
    environment: Environment


class TableApp(App):
    VENV_HEADERS = [
        "Path",
        "Type",
        "Last Modified",
        "Size",
        "Size (Human Readable)",
        "Health",
        "Status",
    ]
    PIPX_HEADERS = ["Package", "Size", "Size (Human Readable)", "Status"]
    VENV_COL_PATH = 0
    VENV_COL_TYPE = 1
    VENV_COL_LAST_MODIFIED = 2
    VENV_COL_SIZE = 3
    VENV_COL_SIZE_HUMAN = 4
    VENV_COL_HEALTH = 5
    VENV_COL_STATUS = 6

    PIPX_COL_PACKAGE = 0
    PIPX_COL_SIZE = 1
    PIPX_COL_SIZE_HUMAN = 2
    PIPX_COL_STATUS = 3

    SPINNER_FRAMES = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]

    def __init__(
        self,
        root_dir: Path | None = None,
        excluded: set[str] | None = None,
        *args: Any,
        **kwargs: Any,
    ):
        super().__init__(*args, **kwargs)
        self.app_version = self.get_app_version()
        self.root_dir = root_dir or Path.cwd()
        self.venv_rows: list[VenvRow] = []
        self.pipx_rows: list[PipxRow] = []
        self.sort_state: dict[str, tuple[int, bool]] = {}
        self.bytes_release: int = 0
        self._spinner_idx: int = 0
        self._spinner_timer = None
        self._scan_counts: tuple[int, int, int, int] = (0, 0, 0, 0)
        self._filter_query: str = ""
        self._venv_display_indices: list[int] = []
        self._multi_select_mode: bool = False
        self._selected_venv_indices: set[int] = set()
        self._health_by_path: dict[str, str] = {}
        self.cleaner = Cleaner()
        self.scanner = Scanner(
            types={
                "venv",
                "pyenv",
                "poetry",
                "conda",
                "pipx",
                "hatch",
                "uv",
                "pipenv",
                "tox",
            },
            excluded=excluded or set(),
        )

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
        Binding(
            key="j", action="cursor_down_active", description="Move down", show=False
        ),
        Binding(key="k", action="cursor_up_active", description="Move up", show=False),
        Binding(key="o", action="open_folder", description="Open folder", show=True),
        Binding(key="slash", action="start_search", description="Filter /", show=True),
        Binding(
            key="t",
            action="toggle_multi_select",
            description="Multi-select T",
            show=True,
        ),
        Binding(
            key="space",
            action="multi_select_toggle_row",
            description="Select row",
            show=False,
        ),
        Binding(
            key="a", action="multi_select_all", description="Select all", show=False
        ),
    ]

    CSS = """
    #banner {
        color: white;
        border: heavy green;
    }

    #loading-display {
        height: 3;
        border: round green;
        padding: 0 1;
        color: green;
    }

    #status-label {
        height: 1;
        color: $text-muted;
    }

    #selected-path-label {
        height: 1;
        color: $text-muted;
    }

    #search-input {
        display: none;
        height: 1;
    }

    #search-input.visible {
        display: block;
    }

    #multi-select-label {
        display: none;
        height: 1;
        color: yellow;
    }

    #multi-select-label.visible {
        display: block;
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
        yield Static("", id="loading-display")
        yield Label("", id="status-label")
        yield Label("", id="selected-path-label")
        yield Input(
            placeholder="Filter by path (regex)… Esc to clear",
            id="search-input",
        )
        yield Label("", id="multi-select-label")

        with TabbedContent():
            with TabPane("Environments", id="venv-tab"):
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

    def add_venv_environment(self, environment: Environment) -> None:
        data_index = len(self.venv_rows)
        self.venv_rows.append(
            {
                "path": str(environment.path),
                "type": environment.type,
                "last_modified": environment.last_accessed_str,
                "size": environment.size_bytes,
                "size_human": environment.size_human,
                "health": self._health_by_path.get(str(environment.path), ""),
                "status": "",
                "environment": environment,
            }
        )
        self._venv_display_indices.append(data_index)

        table = self.query_one("#venv-table", DataTable)
        row = self.venv_rows[-1]
        type_label = ("\u26a0\ufe0f " if environment.is_system_critical else "") + row[
            "type"
        ]
        table.add_row(
            shorten_path_for_table(row["path"]),
            type_label,
            row["last_modified"],
            row["size"],
            row["size_human"],
            _health_text(row["health"]),
            row["status"],
        )

    def add_pipx_environment(self, environment: Environment) -> None:
        self.pipx_rows.append(
            {
                "package": environment.name,
                "size": environment.size_bytes,
                "size_human": environment.size_human,
                "status": "",
                "environment": environment,
            }
        )

        table = self.query_one("#pipx-table", DataTable)
        row = self.pipx_rows[-1]
        table.add_row(row["package"], row["size"], row["size_human"], row["status"])

    def render_venv_table(self) -> None:
        table = self.query_one("#venv-table", DataTable)
        table.clear(columns=True)
        table.add_columns(*self.get_headers_for_table("venv-table"))
        self._venv_display_indices = []
        for i, row in enumerate(self.venv_rows):
            if self._filter_query:
                try:
                    if not re.search(self._filter_query, row["path"], re.IGNORECASE):
                        continue
                except re.error:
                    pass  # invalid regex — show all
            self._venv_display_indices.append(i)
            env = row["environment"]
            type_label = ("\u26a0\ufe0f " if env.is_system_critical else "") + row[
                "type"
            ]
            table.add_row(
                shorten_path_for_table(row["path"]),
                type_label,
                row["last_modified"],
                row["size"],
                row["size_human"],
                _health_text(row["health"]),
                self._compute_row_status(i, row),
            )

    def render_pipx_table(self) -> None:
        table = self.query_one("#pipx-table", DataTable)
        table.clear(columns=True)
        table.add_columns(*self.get_headers_for_table("pipx-table"))
        for row in self.pipx_rows:
            table.add_row(row["package"], row["size"], row["size_human"], row["status"])

    # ------------------------------------------------------------------ #
    #  Row resolution helpers (filter-aware)                              #
    # ------------------------------------------------------------------ #

    def _resolve_venv_row(self, display_row: int) -> tuple[int, VenvRow] | None:
        """Return (data_index, row_dict) for *display_row*, or None when out of range."""  # noqa: E501
        if 0 <= display_row < len(self._venv_display_indices):
            data_index = self._venv_display_indices[display_row]
            return data_index, self.venv_rows[data_index]
        return None

    def _compute_row_status(self, data_index: int, row: VenvRow) -> str:
        """Return the status string to display, taking multi-select into account."""
        if row["status"] == EnvStatus.DELETED.value:
            return EnvStatus.DELETED.value
        if self._multi_select_mode and data_index in self._selected_venv_indices:
            return "\u25cf SELECTED"
        return row["status"]

    def _update_multi_select_label(self) -> None:
        label = self.query_one("#multi-select-label", Label)
        if self._multi_select_mode:
            n = len(self._selected_venv_indices)
            label.add_class("visible")
            label.update(
                f"[bold yellow]Multi-select[/bold yellow] — "
                f"{n} selected | "
                "[dim]Space[/dim]: toggle  "
                "[dim]A[/dim]: all  "
                "[dim]Ctrl+D[/dim]: delete  "
                "[dim]T[/dim]: exit"
            )
        else:
            label.remove_class("visible")
            label.update("")

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
        elif column_index == self.VENV_COL_HEALTH:
            _order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2, "": 3}
            self.venv_rows.sort(
                key=lambda row: _order.get(row["health"], 3), reverse=reverse
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

    def _tick_spinner(self) -> None:
        self._spinner_idx = (self._spinner_idx + 1) % len(self.SPINNER_FRAMES)
        frame = self.SPINNER_FRAMES[self._spinner_idx]
        completed, total, venv_count, pipx_count = self._scan_counts
        progress_str = f"({completed}/{total})" if total else ""
        self.query_one("#loading-display", Static).update(
            f"{frame}  [bold]Scanning environments...[/bold]  [dim]{progress_str}[/dim]\n"  # noqa: E501
            f"   [yellow]{venv_count}[/yellow] environments found"
            f"  ·  [cyan]{pipx_count}[/cyan] pipx packages found"
        )

    async def load_initial_data(self) -> None:
        loading_display = self.query_one("#loading-display", Static)
        status_label = self.query_one("#status-label", Label)
        self.setup_tables()

        self._scan_counts = (0, 0, 0, 0)
        loading_display.display = True
        self._spinner_timer = self.set_interval(0.08, self._tick_spinner)  # type: ignore[assignment]

        applicable_detectors = [
            detector for detector in self.scanner._detectors if detector.can_handle()
        ]
        total_tasks = len(applicable_detectors)
        completed_tasks = 0
        venv_count = 0
        pipx_count = 0
        seen_venv_paths: set[Path] = set()

        async for _detector, environments in self.scanner.scan_async(self.root_dir):
            for environment in environments:
                if environment.type == "pipx":
                    self.add_pipx_environment(environment)
                    pipx_count += 1
                else:
                    try:
                        resolved_path = environment.path.resolve()
                    except OSError:
                        resolved_path = environment.path
                    if resolved_path in seen_venv_paths:
                        continue
                    seen_venv_paths.add(resolved_path)
                    self.add_venv_environment(environment)
                    venv_count += 1
            completed_tasks += 1
            self._scan_counts = (completed_tasks, total_tasks, venv_count, pipx_count)

        self._spinner_timer.stop()  # type: ignore[attr-defined]
        loading_display.display = False
        status_label.update(
            f"Found {venv_count} virtual environments and {pipx_count} pipx packages"
        )
        await self._compute_health_scores()

    async def _compute_health_scores(self) -> None:
        """Score venv environments and populate the Health column."""
        if not self.venv_rows:
            return
        envs = [row["environment"] for row in self.venv_rows]
        scored = await asyncio.to_thread(lambda: score_all(envs, run_git=False))
        engine = SuggestionEngine()
        suggestions = engine.classify_all(scored)
        for suggestion in suggestions:
            self._health_by_path[str(suggestion.env_path)] = suggestion.category
        for row in self.venv_rows:
            row["health"] = self._health_by_path.get(row["path"], "")
        self.render_venv_table()

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

        resolved = self._resolve_venv_row(row_index)
        if resolved:
            _, row = resolved
            selected_path_label.update(f"Selected: {row['path']}")

    @is_venv_tab
    def action_confirm_delete(self):
        if self._multi_select_mode and self._selected_venv_indices:
            # Multi-select mode: delete all selected rows
            for data_index in list(self._selected_venv_indices):
                row = self.venv_rows[data_index]
                if row["status"] == EnvStatus.DELETED.value:
                    continue
                if self.delete_environment(row["environment"]):
                    self.bytes_release += int(row["size"])
                    row["status"] = EnvStatus.DELETED.value
            self._selected_venv_indices.clear()
        else:
            # Normal mode: delete all rows marked for deletion
            for row in self.venv_rows:
                if row["status"] != EnvStatus.MARKED_TO_DELETE.value:
                    continue
                if self.delete_environment(row["environment"]):
                    self.bytes_release += int(row["size"])
                    row["status"] = EnvStatus.DELETED.value

        self.render_venv_table()
        self.query_one("#status-label", Label).update(
            f"{format_size(self.bytes_release)} deleted"
        )
        self.bell()

    @is_venv_tab
    def action_mark_for_delete(self):
        table = self.query_one("#venv-table", DataTable)

        cursor_cell = table.cursor_coordinate
        if cursor_cell:
            resolved = self._resolve_venv_row(cursor_cell.row)
            if not resolved:
                return
            data_index, row = resolved
            current_status = row["status"]
            if current_status == EnvStatus.DELETED.value:
                return
            elif current_status == EnvStatus.MARKED_TO_DELETE.value:
                row["status"] = ""
                table.update_cell_at((cursor_cell.row, self.VENV_COL_STATUS), "")
            else:
                row["status"] = EnvStatus.MARKED_TO_DELETE.value
                table.update_cell_at(
                    (cursor_cell.row, self.VENV_COL_STATUS),
                    EnvStatus.MARKED_TO_DELETE.value,
                )

    @is_venv_tab
    def action_delete_now(self):
        table = self.query_one("#venv-table", DataTable)
        cursor_cell = table.cursor_coordinate
        if cursor_cell:
            resolved = self._resolve_venv_row(cursor_cell.row)
            if not resolved:
                return
            data_index, row = resolved
            if row["status"] == EnvStatus.DELETED.value:
                return
            if self.delete_environment(row["environment"]):
                self.bytes_release += int(row["size"])
                row["status"] = EnvStatus.DELETED.value
                table.update_cell_at(
                    (cursor_cell.row, self.VENV_COL_STATUS),
                    EnvStatus.DELETED.value,
                )
                self.query_one("#status-label", Label).update(
                    f"{format_size(self.bytes_release)} deleted"
                )
        self.bell()

    @is_venv_tab
    def delete_environment(self, environment: Environment) -> bool:
        try:
            self.cleaner.delete(environment)
            return True
        except CleanerError as error:
            self.query_one("#status-label", Label).update(str(error))
            return False

    @is_pipx_tab
    def action_uninstall_pipx(self):
        table = self.query_one("#pipx-table", DataTable)
        cursor_cell = table.cursor_coordinate
        if cursor_cell:
            row = self.pipx_rows[cursor_cell.row]
            if row["status"] == EnvStatus.DELETED.value:
                return
            if self.delete_environment(row["environment"]):
                row["status"] = EnvStatus.DELETED.value
                table.update_cell_at((cursor_cell.row, 3), EnvStatus.DELETED.value)
                self.bytes_release += int(row["size"])
                self.query_one("#status-label", Label).update(
                    f"{format_size(self.bytes_release)} deleted"
                )

        self.bell()

    # ------------------------------------------------------------------ #
    #  New actions: navigation, search, open folder, multi-select         #
    # ------------------------------------------------------------------ #

    def action_cursor_down_active(self) -> None:
        """Move cursor down in the currently focused DataTable (j key)."""
        focused = self.focused
        if isinstance(focused, DataTable):
            focused.action_cursor_down()
        else:
            active = self.query_one(TabbedContent).active
            tid = "#venv-table" if active == "venv-tab" else "#pipx-table"
            self.query_one(tid, DataTable).action_cursor_down()

    def action_cursor_up_active(self) -> None:
        """Move cursor up in the currently focused DataTable (k key)."""
        focused = self.focused
        if isinstance(focused, DataTable):
            focused.action_cursor_up()
        else:
            active = self.query_one(TabbedContent).active
            tid = "#venv-table" if active == "venv-tab" else "#pipx-table"
            self.query_one(tid, DataTable).action_cursor_up()

    @is_venv_tab
    def action_open_folder(self) -> None:
        """Open the parent directory of the selected environment in the OS file manager."""  # noqa: E501
        table = self.query_one("#venv-table", DataTable)
        cursor_cell = table.cursor_coordinate
        if not cursor_cell:
            return
        resolved = self._resolve_venv_row(cursor_cell.row)
        if not resolved:
            return
        _, row = resolved
        parent = str(Path(row["path"]).parent)
        try:
            if sys.platform == "darwin":
                subprocess.Popen(["open", parent])
            elif sys.platform == "win32":
                subprocess.Popen(["explorer", parent])
            else:
                subprocess.Popen(["xdg-open", parent])
        except OSError as exc:
            self.query_one("#status-label", Label).update(f"Cannot open folder: {exc}")

    def action_start_search(self) -> None:
        """Show the search/filter input bar and focus it."""
        search_input = self.query_one("#search-input", Input)
        search_input.add_class("visible")
        search_input.focus()

    def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id == "search-input":
            self._filter_query = event.value
            self.render_venv_table()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id == "search-input":
            if not event.value:
                self._filter_query = ""
                event.input.remove_class("visible")
            self.query_one("#venv-table", DataTable).focus()

    def on_key(self, event) -> None:  # type: ignore[override]
        """Handle Escape to clear and close the search bar."""
        if event.key == "escape":
            search_input = self.query_one("#search-input", Input)
            if "visible" in search_input.classes:
                self._filter_query = ""
                search_input.value = ""
                search_input.remove_class("visible")
                self.render_venv_table()
                active = self.query_one(TabbedContent).active
                tid = "#venv-table" if active == "venv-tab" else "#pipx-table"
                self.query_one(tid, DataTable).focus()
                event.stop()

    def action_toggle_multi_select(self) -> None:
        """Toggle multi-select mode on/off (T key)."""
        self._multi_select_mode = not self._multi_select_mode
        if not self._multi_select_mode:
            self._selected_venv_indices.clear()
        self._update_multi_select_label()
        self.render_venv_table()

    @is_venv_tab
    def action_multi_select_toggle_row(self) -> None:
        """Toggle current row selection in multi-select mode (Space key)."""
        if not self._multi_select_mode:
            return
        table = self.query_one("#venv-table", DataTable)
        cursor_cell = table.cursor_coordinate
        if not cursor_cell:
            return
        resolved = self._resolve_venv_row(cursor_cell.row)
        if not resolved:
            return
        data_index, row = resolved
        if row["status"] == EnvStatus.DELETED.value:
            return
        if data_index in self._selected_venv_indices:
            self._selected_venv_indices.discard(data_index)
        else:
            self._selected_venv_indices.add(data_index)
        self._update_multi_select_label()
        table.update_cell_at(
            (cursor_cell.row, self.VENV_COL_STATUS),
            self._compute_row_status(data_index, row),
        )

    @is_venv_tab
    def action_multi_select_all(self) -> None:
        """Toggle select-all / deselect-all in multi-select mode (A key)."""
        if not self._multi_select_mode:
            return
        non_deleted = {
            i
            for i in self._venv_display_indices
            if self.venv_rows[i]["status"] != EnvStatus.DELETED.value
        }
        if non_deleted == self._selected_venv_indices:
            self._selected_venv_indices.clear()
        else:
            self._selected_venv_indices = non_deleted
        self._update_multi_select_label()
        self.render_venv_table()
