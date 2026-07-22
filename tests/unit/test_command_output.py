"""Coverage for the human-facing output paths that JSON-focused tests miss.

Targets the "Group C" gaps identified in the coverage audit:

* ``killpy doctor`` Rich rendering — ``--all`` category tables, the MEDIUM-only
  and all-active recommendation branches, and naive-datetime handling.
* ``killpy stats --history`` — empty, populated and JSON variants.
* ``killpy list --json-stream`` and the live progress callback.
* the ``analyze_environments`` convenience pipeline.

Scanner / score_all are stubbed so no real filesystem scan happens; the real
``SuggestionEngine`` runs so categories are exercised end to end.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from click.testing import CliRunner

from killpy.__main__ import cli
from killpy.intelligence import analyze_environments
from killpy.intelligence.tracker import UsageTracker
from killpy.models import Environment, GitInfo, ScoredEnvironment

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _env(
    name: str,
    *,
    age_days: int = 200,
    size: int = 100_000_000,
    naive: bool = False,
    env_type: str = "venv",
) -> Environment:
    """Build an Environment whose last-access age is ``age_days`` days ago."""
    la = datetime.now(tz=timezone.utc) - timedelta(days=age_days)
    if naive:
        la = la.replace(tzinfo=None)
    return Environment(
        path=Path(f"/fake/{name}"),
        name=name,
        type=env_type,
        last_modified=la,
        size_bytes=size,
    )


def _scored(
    env: Environment,
    *,
    is_orphan: bool,
    git_active: bool | None = None,
    score: float = 0.5,
) -> ScoredEnvironment:
    """Wrap *env* with the scoring metadata the SuggestionEngine reads."""
    git_info = None
    if git_active is not None:
        git_info = GitInfo(is_git_repo=True, is_active=git_active)
    return ScoredEnvironment(
        env=env,
        score=score,
        explanation=["stub"],
        git_info=git_info,
        has_project_files=not is_orphan,
        is_orphan=is_orphan,
        num_packages=0,
    )


def _high() -> ScoredEnvironment:
    # orphan + >= 180 days → HIGH
    return _scored(_env("orphan_high", age_days=400), is_orphan=True, score=0.9)


def _medium(*, naive: bool = False) -> ScoredEnvironment:
    # not orphan, >= 120 days, no active git → MEDIUM
    return _scored(
        _env("stale_med", age_days=150, naive=naive), is_orphan=False, score=0.6
    )


def _low(*, naive: bool = False) -> ScoredEnvironment:
    # < 120 days → LOW
    return _scored(
        _env("recent_low", age_days=5, naive=naive), is_orphan=False, score=0.1
    )


def _run_doctor(args: list[str], scored: list[ScoredEnvironment]):
    runner = CliRunner()
    with (
        patch("killpy.commands.doctor.Scanner") as mock_scanner,
        patch("killpy.commands.doctor.score_all") as mock_score,
    ):
        mock_scanner.return_value.scan.return_value = [se.env for se in scored]
        mock_score.return_value = scored
        return runner.invoke(cli, ["doctor", "--path", "/tmp", *args])


# ---------------------------------------------------------------------------
# killpy doctor — Rich output paths
# ---------------------------------------------------------------------------


class TestDoctorRichOutput:
    def test_json_empty_has_message_and_empty_suggestions(self) -> None:
        result = _run_doctor(["--json"], [])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["suggestions"] == []
        assert "message" in data

    def test_all_renders_every_category_table(self) -> None:
        # MEDIUM env carries a naive timestamp → exercises the tz branch inside
        # the per-category table renderer.
        result = _run_doctor(["--all"], [_high(), _medium(naive=True), _low()])
        assert result.exit_code == 0
        # One table per non-empty category is rendered.
        assert "HIGH" in result.output
        assert "MEDIUM" in result.output
        assert "LOW" in result.output
        # Environment names surface in the per-category tables.
        assert "orphan_high" in result.output
        assert "stale_med" in result.output
        assert "recent_low" in result.output

    def test_all_skips_empty_category(self) -> None:
        # Only HIGH and LOW present → the MEDIUM iteration hits the empty-category
        # `continue`, so no MEDIUM table is built.
        result = _run_doctor(["--all"], [_high(), _low()])
        assert result.exit_code == 0
        assert "orphan_high" in result.output
        assert "recent_low" in result.output
        # No MEDIUM env → its table (title "Review recommended") is never rendered.
        assert "Review recommended" not in result.output

    def test_default_medium_only_recommendation(self) -> None:
        result = _run_doctor([], [_medium()])
        assert result.exit_code == 0
        # No HIGH → the "review MEDIUM" recommendation branch.
        assert "Review" in result.output
        assert "MEDIUM" in result.output
        # MEDIUM/LOW hidden-count footer is shown in default (non --all) mode.
        assert "hidden" in result.output

    def test_default_all_active_recommendation_and_naive_dates(self) -> None:
        # All LOW and one env carries a naive (tz-less) timestamp, exercising
        # the tz-normalisation branch in both doctor and the SuggestionEngine.
        result = _run_doctor([], [_low(naive=True)])
        assert result.exit_code == 0
        assert "active use" in result.output


# ---------------------------------------------------------------------------
# killpy stats --history
# ---------------------------------------------------------------------------


class TestStatsHistory:
    def _tracker(self, tmp_path: Path, records: int = 0) -> UsageTracker:
        tracker = UsageTracker(tmp_path / "history.json")
        for i in range(records):
            tracker.record_scan_result(
                [_env(f"e{i}", size=1_000)], "/tmp", deleted_bytes=500
            )
        return tracker

    def _run(self, tracker: UsageTracker, args: list[str]):
        runner = CliRunner()
        with patch("killpy.commands.stats.UsageTracker", return_value=tracker):
            return runner.invoke(cli, ["stats", *args])

    def test_history_empty(self, tmp_path: Path) -> None:
        result = self._run(self._tracker(tmp_path), ["--history"])
        assert result.exit_code == 0
        assert "No scan history" in result.output

    def test_history_populated(self, tmp_path: Path) -> None:
        result = self._run(self._tracker(tmp_path, records=2), ["--history"])
        assert result.exit_code == 0
        assert "Scan History" in result.output
        assert "Total scans" in result.output
        assert "2" in result.output

    def test_history_json(self, tmp_path: Path) -> None:
        result = self._run(self._tracker(tmp_path, records=1), ["--history", "--json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["total_scans"] == 1


# ---------------------------------------------------------------------------
# killpy list — json-stream + progress callback
# ---------------------------------------------------------------------------


def _fake_scan(envs: list[Environment]):
    """Stub Scanner.scan that fires the progress callback like the real one."""

    def scan(path, on_progress=None):  # noqa: ANN001, ARG001
        if on_progress is not None:
            on_progress(SimpleNamespace(name="venv"), envs)
        return envs

    return scan


class TestListStreamAndProgress:
    def _ndjson_lines(self, output: str) -> list[dict]:
        return [
            json.loads(line)
            for line in output.splitlines()
            if line.strip().startswith("{")
        ]

    def test_json_stream_emits_one_object_per_env(self) -> None:
        envs = [_env("alpha"), _env("beta")]
        runner = CliRunner()
        with patch("killpy.commands.list.Scanner") as mock_cls:
            mock_cls.return_value.scan.side_effect = _fake_scan(envs)
            result = runner.invoke(cli, ["list", "--path", "/tmp", "--json-stream"])
        assert result.exit_code == 0
        rows = self._ndjson_lines(result.output)
        assert [r["name"] for r in rows] == ["alpha", "beta"]

    def test_json_stream_quiet_still_emits(self) -> None:
        envs = [_env("solo")]
        runner = CliRunner()
        with patch("killpy.commands.list.Scanner") as mock_cls:
            mock_cls.return_value.scan.side_effect = _fake_scan(envs)
            result = runner.invoke(
                cli, ["list", "--path", "/tmp", "--json-stream", "--quiet"]
            )
        assert result.exit_code == 0
        assert len(self._ndjson_lines(result.output)) == 1

    def test_default_run_lists_env(self) -> None:
        envs = [_env("proj")]
        runner = CliRunner()
        with patch("killpy.commands.list.Scanner") as mock_cls:
            mock_cls.return_value.scan.side_effect = _fake_scan(envs)
            result = runner.invoke(cli, ["list", "--path", "/tmp"])
        assert result.exit_code == 0
        assert "proj" in result.output

    def test_quiet_run_still_lists_env(self) -> None:
        envs = [_env("proj")]
        runner = CliRunner()
        with patch("killpy.commands.list.Scanner") as mock_cls:
            mock_cls.return_value.scan.side_effect = _fake_scan(envs)
            result = runner.invoke(cli, ["list", "--path", "/tmp", "--quiet"])
        assert result.exit_code == 0
        assert "proj" in result.output


# ---------------------------------------------------------------------------
# intelligence.analyze_environments — convenience pipeline
# ---------------------------------------------------------------------------


def test_analyze_environments_runs_full_pipeline() -> None:
    suggestions = analyze_environments([_env("x", age_days=400)], run_git=False)
    assert len(suggestions) == 1
    # A 400-day env with no active git is stale — never LOW — and the pipeline
    # must yield an actionable recommendation.
    assert suggestions[0].category in {"HIGH", "MEDIUM"}
    assert suggestions[0].recommended_action
