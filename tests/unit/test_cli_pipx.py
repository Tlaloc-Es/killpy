"""Regression tests for the pipx tab of the TUI (``killpy/cli.py``).

Reuses the headless-app helpers from ``test_cli_multiselect``.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from pathlib import Path

from textual.widgets import TabbedContent

from killpy.cli import EnvStatus
from killpy.models import Environment
from tests.unit.test_cli_multiselect import _make_app


def _make_pipx_env(name: str, size: int) -> Environment:
    return Environment(
        path=Path(f"/data/pipx/venvs/{name}"),
        name=name,
        type="pipx",
        last_modified=datetime(2024, 1, 1, tzinfo=timezone.utc),
        size_bytes=size,
        managed_by="pipx",
    )


def test_uninstall_pipx_from_pipx_tab(tmp_path: Path) -> None:
    """Pressing ``U`` on the pipx tab must uninstall the highlighted package."""

    async def scenario() -> None:
        app, cleaner = _make_app(tmp_path)
        env = _make_pipx_env("httpie", 1234)

        async with app.run_test() as pilot:
            await pilot.pause()
            await app.workers.wait_for_complete()
            app.add_pipx_environment(env)
            await pilot.pause()

            # Still on the venv tab: the action must be gated off.
            app.action_uninstall_pipx()
            assert cleaner.deleted == []

            app.query_one(TabbedContent).active = "pipx-tab"
            await pilot.pause()

            app.action_uninstall_pipx()
            await pilot.pause()

        assert cleaner.deleted == [env]
        assert app.pipx_rows[0]["status"] == EnvStatus.DELETED.value
        assert app.bytes_release == 1234

    asyncio.run(scenario())


def test_uninstall_pipx_skips_already_deleted_row(tmp_path: Path) -> None:
    """A second ``U`` on the same row must not uninstall twice."""

    async def scenario() -> None:
        app, cleaner = _make_app(tmp_path)
        env = _make_pipx_env("httpie", 1234)

        async with app.run_test() as pilot:
            await pilot.pause()
            await app.workers.wait_for_complete()
            app.add_pipx_environment(env)
            await pilot.pause()

            app.query_one(TabbedContent).active = "pipx-tab"
            await pilot.pause()

            app.action_uninstall_pipx()
            app.action_uninstall_pipx()
            await pilot.pause()

        assert cleaner.deleted == [env]
        assert app.bytes_release == 1234

    asyncio.run(scenario())
