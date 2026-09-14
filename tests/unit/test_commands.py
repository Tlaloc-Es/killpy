"""Unit tests for the CLI commands (list, delete, stats, clean).

Uses ``click.testing.CliRunner`` for full command invocation and
stubs ``Scanner`` / ``Cleaner`` to avoid real filesystem scans.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import click
import pytest
from click.testing import CliRunner, Result

from killpy.__main__ import cli
from killpy.cleaner import CleanerError
from killpy.commands._utils import SIZE
from killpy.intelligence.tracker import UsageTracker
from killpy.models import Environment, ScoredEnvironment

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _env(
    path: Path | None = None,
    name: str = "myenv",
    env_type: str = "venv",
    size: int = 1024,
    managed_by: str | None = None,
    critical: bool = False,
) -> Environment:
    return Environment(
        path=path or Path("/fake/myenv"),
        name=name,
        type=env_type,
        last_modified=datetime(2024, 3, 15, tzinfo=timezone.utc),
        size_bytes=size,
        managed_by=managed_by,
        is_system_critical=critical,
    )


def _mock_scanner(envs: list[Environment]):
    """Return a patch context that replaces Scanner.scan with a stub."""
    mock = MagicMock()
    mock.return_value.scan.return_value = envs
    return (
        patch("killpy.commands.list.Scanner", mock),
        patch("killpy.commands.stats.Scanner", mock),
    )


# ---------------------------------------------------------------------------
# --min-size parsing
# ---------------------------------------------------------------------------


class TestSizeParamType:
    def test_accepts_an_already_converted_value(self) -> None:
        # click hands the type its own output back in some flows (defaults,
        # re-prompts), so conversion has to be idempotent.
        assert SIZE.convert(4096, None, None) == 4096

    def test_parses_every_supported_unit(self) -> None:
        assert SIZE.convert("512B", None, None) == 512
        assert SIZE.convert("2KB", None, None) == 2 << 10
        assert SIZE.convert("2KiB", None, None) == 2 << 10
        assert SIZE.convert("1.5GB", None, None) == int(1.5 * (1 << 30))
        assert SIZE.convert("1.5GiB", None, None) == int(1.5 * (1 << 30))
        assert SIZE.convert("1TB", None, None) == 1 << 40
        assert SIZE.convert("1TiB", None, None) == 1 << 40

    def test_is_case_and_whitespace_insensitive(self) -> None:
        assert SIZE.convert(" 4 mb ", None, None) == 4 << 20

    @pytest.mark.parametrize(
        "value",
        [
            "lots",  # not a number at all
            "1000",  # no unit
            "-5MB",  # negative
            "",  # empty
            "1,5GB",  # comma decimal
            "infMB",  # float sentinel
            "٥MB",  # non-ASCII digits
        ],
    )
    def test_rejects_invalid_sizes(self, value: str) -> None:
        with pytest.raises(click.UsageError):
            SIZE.convert(value, None, None)

    def test_huge_values_do_not_overflow(self) -> None:
        # A float mantissa turns 309+ digits into infinity and int() then
        # raises; an absurd threshold should just match nothing instead.
        assert SIZE.convert("9" * 309 + "MB", None, None) > 10**300


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

    def test_min_size_filters_and_accepts_decimal_units(self) -> None:
        envs = [
            _env(name="small", size=1 << 30),
            _env(name="large", size=2 << 30),
        ]
        result = self._run(["--min-size", "1.5GB"], envs=envs)
        assert result.exit_code == 0
        assert "large" in result.output
        assert "small" not in result.output

    def test_invalid_min_size_is_a_usage_error(self) -> None:
        result = self._run(["--min-size", "lots"])
        assert result.exit_code == 2
        assert "must be a size" in result.output

    def test_min_size_applies_to_the_streamed_output(self) -> None:
        # --json-stream filters inside the per-detector callback, a separate
        # call site from the batch path above.
        batch = [_env(name="small", size=1023), _env(name="large", size=4096)]

        def fake_scan(path, on_progress=None):
            on_progress(SimpleNamespace(name="venv"), batch)
            return batch

        runner = CliRunner()
        with patch("killpy.commands.list.Scanner") as mock_cls:
            mock_cls.return_value.scan.side_effect = fake_scan
            result = runner.invoke(
                cli,
                ["list", "--path", "/tmp", "--json-stream", "-q", "--min-size", "1KB"],
            )

        assert result.exit_code == 0
        names = [json.loads(line)["name"] for line in result.output.splitlines()]
        assert names == ["large"]


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

    def test_min_size_filters_aggregates(self) -> None:
        envs = [_env(name="small", size=1023), _env(name="large", size=1024)]
        result = self._run(["--min-size", "1KB", "--json"], envs=envs)
        data = json.loads(result.output)
        assert data["total_count"] == 1
        assert data["total_size_bytes"] == 1024

    def test_history_rejects_min_size(self) -> None:
        runner = CliRunner()
        result = runner.invoke(cli, ["stats", "--history", "--min-size", "1MB"])
        assert result.exit_code == 2
        assert "--history" in result.output
        assert "--min-size" in result.output

    def test_history_rejects_explicit_path(self) -> None:
        runner = CliRunner()
        result = runner.invoke(cli, ["stats", "--history", "--path", "/tmp"])
        assert result.exit_code == 2
        assert "--history" in result.output
        assert "--path" in result.output


# ---------------------------------------------------------------------------
# killpy delete
# ---------------------------------------------------------------------------


class TestDeleteCommand:
    def _run(
        self, args: list[str], envs: list[Environment] | None = None, input: str = "y\n"
    ):
        runner = CliRunner()
        envs = envs or []
        with (
            patch("killpy.commands.delete.Scanner") as mock_scanner,
            patch("killpy.commands.delete.Cleaner") as mock_cleaner,
        ):
            mock_scanner.return_value.scan.return_value = envs
            mock_cleaner.return_value.delete.side_effect = lambda e: e.size_bytes
            result = runner.invoke(
                cli, ["delete", "--path", "/tmp"] + args, input=input
            )
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
            result = runner.invoke(
                cli, ["delete", "--path", "/tmp", "--dry-run", "--yes"]
            )
        mock_cleaner.return_value.delete.assert_not_called()
        assert "Dry run" in result.output

    def test_skips_system_critical_by_default(self) -> None:
        """In-use environments are skipped and reported, not deleted."""
        envs = [_env(name="normal"), _env(name="active", critical=True)]
        with (
            patch("killpy.commands.delete.Scanner") as mock_scanner,
            patch("killpy.commands.delete.Cleaner") as mock_cleaner,
        ):
            mock_scanner.return_value.scan.return_value = envs
            mock_cleaner.return_value.delete.side_effect = lambda e: e.size_bytes
            runner = CliRunner()
            result = runner.invoke(cli, ["delete", "--path", "/tmp", "--yes"])
        assert result.exit_code == 0
        assert "currently in use" in result.output
        deleted = [
            call.args[0] for call in mock_cleaner.return_value.delete.call_args_list
        ]
        assert [e.name for e in deleted] == ["normal"]

    def test_force_includes_system_critical(self) -> None:
        envs = [_env(name="active", critical=True)]
        with (
            patch("killpy.commands.delete.Scanner") as mock_scanner,
            patch("killpy.commands.delete.Cleaner") as mock_cleaner,
        ):
            mock_scanner.return_value.scan.return_value = envs
            mock_cleaner.return_value.delete.side_effect = lambda e: e.size_bytes
            runner = CliRunner()
            result = runner.invoke(
                cli, ["delete", "--path", "/tmp", "--yes", "--force"]
            )
        assert result.exit_code == 0
        assert "currently in use" not in result.output
        deleted = [
            call.args[0] for call in mock_cleaner.return_value.delete.call_args_list
        ]
        assert [e.name for e in deleted] == ["active"]
        assert mock_cleaner.call_args.kwargs.get("force") is True

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
            runner.invoke(cli, ["delete", "--path", "/tmp"], input="n\n")
        mock_cleaner.return_value.delete.assert_not_called()


# ---------------------------------------------------------------------------
# killpy --help
# ---------------------------------------------------------------------------


class TestDeleteFilters:
    """Cover the _filter_envs branches (older_than, type) inside delete_cmd."""

    def _run_delete(self, extra_args: list[str], envs, input: str = "y\n"):
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
        # Only the venv is deleted; the conda env is excluded by the type filter.
        assert result.exit_code == 0
        assert "Deleted a" in result.output
        assert "Deleted b" not in result.output

    def test_older_than_filter(self) -> None:
        old = _env(name="old", env_type="venv")
        # last_modified is datetime(2024, 3, 15, tzinfo=utc) — more than 30 days ago
        result = self._run_delete(["--older-than", "1", "--yes"], [old])
        # The stale env passes the filter and is actually deleted.
        assert result.exit_code == 0
        assert "Deleted old" in result.output

    def test_min_size_filter(self) -> None:
        envs = [_env(name="small", size=1023), _env(name="large", size=1024)]
        result = self._run_delete(["--min-size", "1KB", "--yes"], envs)
        assert result.exit_code == 0
        assert "Deleted large" in result.output
        assert "Deleted small" not in result.output

    def test_cleaner_error_shows_message_and_exits_nonzero(self) -> None:
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


class TestDeleteHistoryRecording:
    """`killpy delete` must persist a scan record and the freed bytes so that
    `killpy stats --history` reflects real cleanups (regression: record_scan
    was never called, leaving history permanently empty)."""

    def test_delete_populates_history(self, tmp_path: Path) -> None:
        tracker = UsageTracker(tmp_path / "history.json")
        envs = [_env(name="proj_a", size=2048), _env(name="proj_b", size=1024)]
        with (
            patch("killpy.commands.delete.Scanner") as mock_scanner,
            patch("killpy.commands.delete.Cleaner") as mock_cleaner,
            patch("killpy.commands.delete.UsageTracker", return_value=tracker),
        ):
            mock_scanner.return_value.scan.return_value = envs
            mock_cleaner.return_value.delete.side_effect = lambda e: e.size_bytes
            result = CliRunner().invoke(cli, ["delete", "--path", "/tmp", "--yes"])

        assert result.exit_code == 0
        records = tracker.get_history()
        assert len(records) == 1
        assert records[0].environments_count == 2
        assert records[0].total_space_found == 3072
        assert records[0].total_space_deleted == 3072

    def test_dry_run_does_not_touch_history(self, tmp_path: Path) -> None:
        tracker = UsageTracker(tmp_path / "history.json")
        with (
            patch("killpy.commands.delete.Scanner") as mock_scanner,
            patch("killpy.commands.delete.UsageTracker", return_value=tracker),
        ):
            mock_scanner.return_value.scan.return_value = [_env(name="x")]
            CliRunner().invoke(cli, ["delete", "--path", "/tmp", "--dry-run", "--yes"])

        assert tracker.get_history() == []
        assert not (tmp_path / "history.json").exists()


class TestHelpOutput:
    def test_main_help_lists_subcommands(self) -> None:
        runner = CliRunner()
        result = runner.invoke(cli, ["--help"])
        assert result.exit_code == 0
        assert "list" in result.output
        assert "delete" in result.output
        assert "stats" in result.output
        assert "clean" in result.output
        assert "doctor" in result.output

    def test_list_help(self) -> None:
        runner = CliRunner()
        result = runner.invoke(cli, ["list", "--help"])
        assert result.exit_code == 0
        assert "--json" in result.output
        assert "--type" in result.output
        assert "--sort" in result.output
        assert "--reverse" in result.output

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


# ---------------------------------------------------------------------------
# killpy doctor
# ---------------------------------------------------------------------------


class TestDoctorCommand:
    def _run(self, args: list[str], envs: list[Environment] | None = None) -> Result:
        runner = CliRunner()
        envs = envs or []
        with (
            patch("killpy.commands.doctor.Scanner") as mock_scanner,
            patch("killpy.commands.doctor.score_all") as mock_score,
        ):
            mock_scanner.return_value.scan.return_value = envs
            # score_all returns ScoredEnvironment stubs for the filtered input.
            mock_score.side_effect = lambda filtered, **_kwargs: [
                ScoredEnvironment(
                    env=e,
                    score=0.8,
                    explanation=["stub"],
                    git_info=None,
                    has_project_files=False,
                    is_orphan=True,
                    num_packages=0,
                )
                for e in filtered
            ]
            result = runner.invoke(cli, ["doctor", "--path", "/tmp"] + args)
        return result

    def test_exits_zero_on_empty(self) -> None:
        result = self._run([])
        assert result.exit_code == 0

    def test_no_envs_message(self) -> None:
        result = self._run([])
        assert "No environments found" in result.output

    def test_json_output_structure(self) -> None:
        envs = [_env(name="a", size=1_000_000)]
        result = self._run(["--json"], envs=envs)
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert "total_environments" in data
        assert "suggestions" in data
        assert data["total_environments"] == 1

    def test_rich_output_contains_health_header(self) -> None:
        envs = [_env(name="bigenv", size=500_000_000)]
        result = self._run([], envs=envs)
        assert result.exit_code == 0
        assert "Health" in result.output or "Offender" in result.output

    def test_min_size_filters_before_scoring(self) -> None:
        envs = [_env(name="small", size=1023), _env(name="large", size=1024)]
        result = self._run(["--min-size", "1KB", "--json"], envs=envs)
        assert result.exit_code == 0
        assert json.loads(result.output)["total_environments"] == 1

    def test_doctor_help(self) -> None:
        runner = CliRunner()
        result = runner.invoke(cli, ["doctor", "--help"])
        assert result.exit_code == 0
        assert "--json" in result.output
