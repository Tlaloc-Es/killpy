"""Regression tests for TUI multi-select behaviour (``killpy/cli.py``).

The app runs headless via Textual's ``App.run_test``.  The scanner is
replaced with an empty one (no detectors) so nothing on the real
filesystem is scanned and no subprocesses are spawned; environments are
injected directly and deletions are captured by a recording stub.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from pathlib import Path

from killpy.cli import EnvStatus, TableApp
from killpy.intelligence.tracker import UsageTracker
from killpy.models import Environment
from killpy.scanner import Scanner


class RecordingCleaner:
    """Cleaner stub that records deletions instead of touching the disk."""

    def __init__(self) -> None:
        self.deleted: list[Environment] = []

    def delete(self, env: Environment) -> int:
        self.deleted.append(env)
        return env.size_bytes


def _make_env(path: str, size: int, critical: bool = False) -> Environment:
    return Environment(
        path=Path(path),
        name=path,
        type=".venv",
        last_modified=datetime(2024, 1, 1, tzinfo=timezone.utc),
        size_bytes=size,
        is_system_critical=critical,
    )


def _make_app(tmp_path: Path) -> tuple[TableApp, RecordingCleaner]:
    app = TableApp(root_dir=tmp_path)
    app.scanner = Scanner(detectors=[])
    app.tracker = UsageTracker(storage_path=tmp_path / "history.json")
    cleaner = RecordingCleaner()
    app.cleaner = cleaner  # type: ignore[assignment]
    return app, cleaner


def test_multi_select_deletes_selected_env_after_sort(tmp_path: Path) -> None:
    """Sorting columns must not change which environments get deleted:
    selections are keyed by path, not by row position.
    """

    async def scenario() -> None:
        app, cleaner = _make_app(tmp_path)
        env_small = _make_env("/data/small/.venv", 10)
        env_medium = _make_env("/data/medium/.venv", 20)
        env_big = _make_env("/data/big/.venv", 30)

        async with app.run_test() as pilot:
            await pilot.pause()
            await app.workers.wait_for_complete()
            for env in (env_small, env_medium, env_big):
                app.add_venv_environment(env)
            await pilot.pause()

            app.action_toggle_multi_select()
            # Cursor starts on row 0 → env_small gets selected.
            app.action_multi_select_toggle_row()
            assert app._selected_venv_paths == {str(env_small.path)}

            # Sort by size descending: env_big becomes the first row.
            app.sort_venv_rows(app.VENV_COL_SIZE, reverse=True)
            assert app.venv_rows[0]["environment"] is env_big

            app.action_confirm_delete()
            await pilot.pause()

        assert cleaner.deleted == [env_small]
        deleted_envs = [
            row["environment"]
            for row in app.venv_rows
            if row["status"] == EnvStatus.DELETED.value
        ]
        assert deleted_envs == [env_small]

    asyncio.run(scenario())


def test_multi_select_all_survives_sort(tmp_path: Path) -> None:
    """``A`` (select all) followed by a sort must still delete every row."""

    async def scenario() -> None:
        app, cleaner = _make_app(tmp_path)
        envs = [
            _make_env("/data/a/.venv", 10),
            _make_env("/data/b/.venv", 20),
        ]

        async with app.run_test() as pilot:
            await pilot.pause()
            await app.workers.wait_for_complete()
            for env in envs:
                app.add_venv_environment(env)
            await pilot.pause()

            app.action_toggle_multi_select()
            app.action_multi_select_all()
            app.sort_venv_rows(app.VENV_COL_SIZE, reverse=True)
            app.action_confirm_delete()
            await pilot.pause()

        assert sorted(str(e.path) for e in cleaner.deleted) == sorted(
            str(e.path) for e in envs
        )

    asyncio.run(scenario())


def test_exiting_multi_select_clears_selection(tmp_path: Path) -> None:
    """Leaving multi-select mode drops the selection entirely."""

    async def scenario() -> None:
        app, cleaner = _make_app(tmp_path)

        async with app.run_test() as pilot:
            await pilot.pause()
            await app.workers.wait_for_complete()
            app.add_venv_environment(_make_env("/data/a/.venv", 10))
            await pilot.pause()

            app.action_toggle_multi_select()
            app.action_multi_select_toggle_row()
            assert app._selected_venv_paths

            app.action_toggle_multi_select()  # exit multi-select
            assert not app._selected_venv_paths

            app.action_toggle_multi_select()  # re-enter
            app.action_confirm_delete()
            await pilot.pause()

        assert cleaner.deleted == []

    asyncio.run(scenario())
