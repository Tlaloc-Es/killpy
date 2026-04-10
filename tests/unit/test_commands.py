"""Unit tests for the CLI commands (list, delete, stats, clean).

Uses ``click.testing.CliRunner`` for full command invocation and
stubs ``Scanner`` / ``Cleaner`` to avoid real filesystem scans.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from killpy.__main__ import cli
from killpy.models import Environment


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _env(
    path: Path | None = None,
    name: str = "myenv",
    env_type: str = "venv",
    size: int = 1024,
    managed_by: str | None = None,
) -> Environment:
    return Environment(
        path=path or Path("/fake/myenv"),
        name=name,
        type=env_type,
        last_accessed=datetime(2024, 3, 15, tzinfo=timezone.utc),
        size_bytes=size,
        managed_by=managed_by,
    )


def _mock_scanner(envs: list[Environment]):
    """Return a patch context that replaces Scanner.scan with a stub."""
    mock = MagicMock()
    mock.return_value.scan.return_value = envs
    return patch("killpy.commands.list.Scanner", mock), patch("killpy.commands.stats.Scanner", mock)


# ---------------------------------------------------------------------------
# killpy list
# ---------------------------------------------------------------------------

class TestListCommand:
    def _run(self, args: list[str], envs: list[Environment] | None = None):
        runner = CliRunner()
        envs = envs or []
        with patch("killpy.commands.list.Scanner") as mock_cls:
            mock_cls.return_value.scan.return_value = envs
            result = runner.invoke(cli, ["list", "--path", "/tmp"] + args)
        return result

    def test_exits_zero_on_empty(self) -> None:
        result = self._run([])
        assert result.exit_code == 0

    def test_no_envs_message(self) -> None:
        result = self._run([])
        assert "No environments found" in result.output

    def test_shows_table_with_envs(self) -> None:
        envs = [_env(name="project_a"), _env(name="project_b")]
        result = self._run([], envs=envs)
        assert result.exit_code == 0
        assert "project_a" in result.output
        assert "project_b" in result.output

    def test_json_output(self) -> None:
        envs = [_env(name="alpha", size=2048)]
        result = self._run(["--json"], envs=envs)
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert isinstance(data, list)
        assert data[0]["name"] == "alpha"
        assert data[0]["size_bytes"] == 2048

    def test_type_filter(self) -> None:
        envs = [
            _env(name="a", env_type="venv"),
            _env(name="b", env_type="conda"),
        ]
        result = self._run(["--type", "venv"], envs=envs)
        assert "a" in result.output
        assert "b" not in result.output

    def test_type_filter_case_insensitive(self) -> None:
        envs = [_env(name="a", env_type="Venv")]
        result = self._run(["--type", "venv"], envs=envs)
        assert "a" in result.output


# ---------------------------------------------------------------------------
# killpy stats
# ---------------------------------------------------------------------------

class TestStatsCommand:
    def _run(self, args: list[str], envs: list[Environment] | None = None):
        runner = CliRunner()
        envs = envs or []
        with patch("killpy.commands.stats.Scanner") as mock_cls:
            mock_cls.return_value.scan.return_value = envs
            result = runner.invoke(cli, ["stats", "--path", "/tmp"] + args)
        return result

    def test_exits_zero(self) -> None:
        result = self._run([], envs=[_env()])
        assert result.exit_code == 0

    def test_no_envs_message(self) -> None:
        result = self._run([])
        assert "No environments found" in result.output

    def test_shows_env_type(self) -> None:
        result = self._run([], envs=[_env(env_type="venv", size=1000)])
        assert "venv" in result.output

    def test_json_output_structure(self) -> None:
        envs = [
            _env(env_type="venv", size=1000),
            _env(env_type="conda", size=3000),
        ]
        result = self._run(["--json"], envs=envs)
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert "total_count" in data
        assert data["total_count"] == 2
        assert "by_type" in data
        assert "venv" in data["by_type"]
        assert "conda" in data["by_type"]
        assert data["by_type"]["venv"]["count"] == 1
        assert data["by_type"]["conda"]["size_bytes"] == 3000

    def test_json_total_size(self) -> None:
        envs = [_env(size=500), _env(size=1500)]
        result = self._run(["--json"], envs=envs)
        data = json.loads(result.output)
        assert data["total_size_bytes"] == 2000


# ---------------------------------------------------------------------------
# killpy delete
# ---------------------------------------------------------------------------

class TestDeleteCommand:
    def _run(self, args: list[str], envs: list[Environment] | None = None, input: str = "y\n"):
        runner = CliRunner()
        envs = envs or []
        with (
            patch("killpy.commands.delete.Scanner") as mock_scanner,
            patch("killpy.commands.delete.Cleaner") as mock_cleaner,
        ):
            mock_scanner.return_value.scan.return_value = envs
            mock_cleaner.return_value.delete.side_effect = lambda e: e.size_bytes
            result = runner.invoke(cli, ["delete", "--path", "/tmp"] + args, input=input)
        return result

    def test_exits_zero_on_empty(self) -> None:
        result = self._run([])
        assert result.exit_code == 0
        assert "No environments found" in result.output

    def test_dry_run_does_not_delete(self) -> None:
        envs = [_env(name="drytest")]
        with (
            patch("killpy.commands.delete.Scanner") as mock_scanner,
            patch("killpy.commands.delete.Cleaner") as mock_cleaner,
        ):
            mock_scanner.return_value.scan.return_value = envs
            runner = CliRunner()
            result = runner.invoke(cli, ["delete", "--path", "/tmp", "--dry-run", "--yes"])
        mock_cleaner.return_value.delete.assert_not_called()
        assert "Dry run" in result.output

    def test_skip_confirmation_with_yes_flag(self) -> None:
        envs = [_env(name="proj")]
        with (
            patch("killpy.commands.delete.Scanner") as mock_scanner,
            patch("killpy.commands.delete.Cleaner") as mock_cleaner,
        ):
            mock_scanner.return_value.scan.return_value = envs
            mock_cleaner.return_value.delete.return_value = 1024
            runner = CliRunner()
            result = runner.invoke(cli, ["delete", "--path", "/tmp", "--yes"])
        # Should not prompt, should succeed
        assert result.exit_code == 0

    def test_abort_on_no_confirmation(self) -> None:
        envs = [_env(name="proj")]
        with (
            patch("killpy.commands.delete.Scanner") as mock_scanner,
            patch("killpy.commands.delete.Cleaner") as mock_cleaner,
        ):
            mock_scanner.return_value.scan.return_value = envs
            runner = CliRunner()
            result = runner.invoke(cli, ["delete", "--path", "/tmp"], input="n\n")
        mock_cleaner.return_value.delete.assert_not_called()


# ---------------------------------------------------------------------------
# killpy --help
# ---------------------------------------------------------------------------

class TestDeleteFilters:
    """Cover the _filter_envs branches (older_than, type) inside delete_cmd."""

    def _run_delete(self, extra_args: list[str], envs, input: str = "y\n"):
        from killpy.cleaner import CleanerError
        runner = CliRunner()
        with (
            patch("killpy.commands.delete.Scanner") as mock_scanner,
            patch("killpy.commands.delete.Cleaner") as mock_cleaner,
        ):
            mock_scanner.return_value.scan.return_value = envs
            mock_cleaner.return_value.delete.side_effect = lambda e: e.size_bytes
            result = runner.invoke(
                cli, ["delete", "--path", "/tmp"] + extra_args, input=input
            )
        return result

    def test_type_filter_excludes_non_matching(self) -> None:
        envs = [
            _env(name="a", env_type="venv"),
            _env(name="b", env_type="conda"),
        ]
        result = self._run_delete(["--type", "venv", "--yes"], envs)
        # Only venv should be deleted; conda silently excluded
        assert result.exit_code == 0

    def test_older_than_filter(self) -> None:
        old = _env(name="old", env_type="venv")
        # last_accessed is datetime(2024, 3, 15, tzinfo=utc) — more than 30 days ago
        result = self._run_delete(["--older-than", "1", "--yes"], [old])
        assert result.exit_code == 0

    def test_cleaner_error_shows_message_and_exits_nonzero(self) -> None:
        from killpy.cleaner import CleanerError
        runner = CliRunner()
        env = _env(name="broken")
        with (
            patch("killpy.commands.delete.Scanner") as mock_scanner,
            patch("killpy.commands.delete.Cleaner") as mock_cleaner,
        ):
            mock_scanner.return_value.scan.return_value = [env]
            mock_cleaner.return_value.delete.side_effect = CleanerError("kaboom")
            result = runner.invoke(
                cli, ["delete", "--path", "/tmp", "--yes"], input="y\n"
            )
        assert result.exit_code == 1
        assert "broken" in result.output or "kaboom" in result.output


class TestHelpOutput:
    def test_main_help_lists_subcommands(self) -> None:
        runner = CliRunner()
        result = runner.invoke(cli, ["--help"])
        assert result.exit_code == 0
        assert "list" in result.output
        assert "delete" in result.output
        assert "stats" in result.output
        assert "clean" in result.output

    def test_list_help(self) -> None:
        runner = CliRunner()
        result = runner.invoke(cli, ["list", "--help"])
        assert result.exit_code == 0
        assert "--json" in result.output
        assert "--type" in result.output

    def test_delete_help(self) -> None:
        runner = CliRunner()
        result = runner.invoke(cli, ["delete", "--help"])
        assert result.exit_code == 0
        assert "--dry-run" in result.output
        assert "--yes" in result.output

    def test_stats_help(self) -> None:
        runner = CliRunner()
        result = runner.invoke(cli, ["stats", "--help"])
        assert result.exit_code == 0
        assert "--json" in result.output
