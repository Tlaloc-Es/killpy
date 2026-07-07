"""The TUI must refuse to delete system-critical (in-use) environments.

Reuses the headless-app helpers from ``test_cli_multiselect``.
"""

from __future__ import annotations

import asyncio
from pathlib import Path

from textual.widgets import Label

from killpy.cli import EnvStatus
from tests.unit.test_cli_multiselect import _make_app, _make_env


def test_delete_now_refuses_system_critical(tmp_path: Path) -> None:
    """Shift+Delete on a ⚠ row must not delete it and must explain why."""

    async def scenario() -> None:
        app, cleaner = _make_app(tmp_path)
        env = _make_env("/data/active/.venv", 10, critical=True)

        async with app.run_test() as pilot:
            await pilot.pause()
            await app.workers.wait_for_complete()
            app.add_venv_environment(env)
            await pilot.pause()

            app.action_delete_now()
            await pilot.pause()

            status_text = str(app.query_one("#status-label", Label).render())
            assert "currently in use" in status_text

        assert cleaner.deleted == []
        assert app.venv_rows[0]["status"] != EnvStatus.DELETED.value

    asyncio.run(scenario())


def test_confirm_delete_skips_marked_critical_row(tmp_path: Path) -> None:
    """Mark (D) + Ctrl+D on a ⚠ row must leave it untouched."""

    async def scenario() -> None:
        app, cleaner = _make_app(tmp_path)
        env_active = _make_env("/data/active/.venv", 10, critical=True)
        env_normal = _make_env("/data/normal/.venv", 20)

        async with app.run_test() as pilot:
            await pilot.pause()
            await app.workers.wait_for_complete()
            app.add_venv_environment(env_active)
            app.add_venv_environment(env_normal)
            await pilot.pause()

            # Mark both rows for deletion (cursor starts on row 0).
            app.action_mark_for_delete()
            table = app.query_one("#venv-table")
            table.move_cursor(row=1)
            app.action_mark_for_delete()

            app.action_confirm_delete()
            await pilot.pause()

        assert cleaner.deleted == [env_normal]
        assert app.venv_rows[0]["status"] != EnvStatus.DELETED.value
        assert app.venv_rows[1]["status"] == EnvStatus.DELETED.value

    asyncio.run(scenario())
