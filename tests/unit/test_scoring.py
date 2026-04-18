"""Unit tests for ``killpy.intelligence.scoring``."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

from killpy.intelligence.scoring import ScoringService, ScoringWeights, score_all
from killpy.models import Environment, GitInfo

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _env(
    path: Path | None = None,
    name: str = "test-env",
    size: int = 100 * 1024 * 1024,  # 100 MB
    last_accessed: datetime | None = None,
) -> Environment:
    return Environment(
        path=path or Path("/fake/test-env"),
        name=name,
        type="venv",
        last_accessed=last_accessed or datetime(2023, 1, 1, tzinfo=timezone.utc),
        size_bytes=size,
        managed_by=None,
    )


_ACTIVE_GIT = GitInfo(is_git_repo=True, is_active=True)
_INACTIVE_GIT = GitInfo(is_git_repo=True, is_active=False)
_NO_GIT = GitInfo(is_git_repo=False, is_active=False)


# ---------------------------------------------------------------------------
# ScoringService._normalize_size
# ---------------------------------------------------------------------------


class TestNormalizeSize:
    def test_zero_bytes_is_zero(self) -> None:
        assert ScoringService._normalize_size(0) == 0.0

    def test_500mb_is_near_half(self) -> None:
        score = ScoringService._normalize_size(500 * 1024 * 1024)
        # sigmoid at the inflection point ≈ 0.5
        assert abs(score - 0.5) < 0.01

    def test_very_large_approaches_one(self) -> None:
        score = ScoringService._normalize_size(10 * 1024 * 1024 * 1024)  # 10 GB
        assert score > 0.95

    def test_small_size_approaches_zero(self) -> None:
        score = ScoringService._normalize_size(1024)  # 1 KB
        assert score < 0.05


# ---------------------------------------------------------------------------
# ScoringService._normalize_age
# ---------------------------------------------------------------------------


class TestNormalizeAge:
    def test_just_accessed_gives_zero(self) -> None:
        la = datetime.now(tz=timezone.utc)
        score, days = ScoringService._normalize_age(la)
        assert score < 0.01
        assert days == 0

    def test_365_days_gives_one(self) -> None:
        la = datetime.now(tz=timezone.utc) - timedelta(days=365)
        score, days = ScoringService._normalize_age(la)
        assert abs(score - 1.0) < 0.01
        assert days == 365

    def test_beyond_365_caps_at_one(self) -> None:
        la = datetime.now(tz=timezone.utc) - timedelta(days=800)
        score, _ = ScoringService._normalize_age(la)
        assert score == 1.0


# ---------------------------------------------------------------------------
# ScoringService._orphan_score
# ---------------------------------------------------------------------------


class TestOrphanScore:
    def test_project_with_pyproject_is_not_orphan(self, tmp_path: Path) -> None:
        (tmp_path / "pyproject.toml").write_text("[project]")
        env = tmp_path / ".venv"
        env.mkdir()
        is_orphan, s = ScoringService._orphan_score(env)
        assert is_orphan is False
        assert s == 0.0

    def test_env_without_project_files_is_orphan(self, tmp_path: Path) -> None:
        env = tmp_path / ".venv"
        env.mkdir()
        is_orphan, s = ScoringService._orphan_score(env)
        assert is_orphan is True
        assert s == 1.0

    def test_requirements_txt_prevents_orphan(self, tmp_path: Path) -> None:
        (tmp_path / "requirements.txt").write_text("")
        env = tmp_path / ".venv"
        env.mkdir()
        is_orphan, _ = ScoringService._orphan_score(env)
        assert is_orphan is False


# ---------------------------------------------------------------------------
# ScoringService._git_inactivity_score
# ---------------------------------------------------------------------------


class TestGitInactivityScore:
    def test_active_git_is_zero(self) -> None:
        assert ScoringService._git_inactivity_score(_ACTIVE_GIT) == 0.0

    def test_inactive_git_is_one(self) -> None:
        assert ScoringService._git_inactivity_score(_INACTIVE_GIT) == 1.0

    def test_no_git_repo_is_neutral(self) -> None:
        assert ScoringService._git_inactivity_score(_NO_GIT) == 0.5

    def test_none_is_neutral(self) -> None:
        assert ScoringService._git_inactivity_score(None) == 0.5


# ---------------------------------------------------------------------------
# ScoringService.score
# ---------------------------------------------------------------------------


class TestScoringServiceScore:
    def test_returns_scored_environment(self, tmp_path: Path) -> None:
        env = _env(path=tmp_path)
        service = ScoringService()
        result = service.score(env)
        assert 0.0 <= result.score <= 1.0
        assert result.env is env

    def test_explanation_list_populated(self, tmp_path: Path) -> None:
        env = _env(path=tmp_path)
        service = ScoringService()
        result = service.score(env, git_info=_ACTIVE_GIT)
        assert len(result.explanation) >= 4

    def test_active_git_lowers_score(self, tmp_path: Path) -> None:
        env = _env(path=tmp_path)
        service = ScoringService()
        score_active = service.score(env, git_info=_ACTIVE_GIT).score
        score_inactive = service.score(env, git_info=_INACTIVE_GIT).score
        assert score_active < score_inactive

    def test_custom_weights_applied(self, tmp_path: Path) -> None:
        env = _env(path=tmp_path, size=10 * 1024 * 1024 * 1024)
        # Make size dominant
        weights = ScoringWeights(
            size_weight=1.0,
            age_weight=0.0,
            orphan_weight=0.0,
            git_inactivity_weight=0.0,
        )
        service = ScoringService(weights)
        result = service.score(env)
        assert result.score > 0.9

    def test_score_is_between_zero_and_one(self, tmp_path: Path) -> None:
        env = _env(path=tmp_path)
        service = ScoringService()
        for git in [_ACTIVE_GIT, _INACTIVE_GIT, _NO_GIT, None]:
            assert 0.0 <= service.score(env, git_info=git).score <= 1.0


# ---------------------------------------------------------------------------
# score_all
# ---------------------------------------------------------------------------


class TestScoreAll:
    def test_sorted_by_score_descending(self, tmp_path: Path) -> None:
        big_old = _env(path=tmp_path / "a", size=2_000_000_000)
        tiny_new = _env(
            path=tmp_path / "b",
            size=1024,
            last_accessed=datetime.now(tz=timezone.utc),
        )
        (tmp_path / "a").mkdir()
        (tmp_path / "b").mkdir()
        results = score_all([big_old, tiny_new], run_git=False)
        assert results[0].env is big_old

    def test_returns_all_envs(self, tmp_path: Path) -> None:
        envs = [_env(path=tmp_path / str(i)) for i in range(3)]
        for i in range(3):
            (tmp_path / str(i)).mkdir()
        results = score_all(envs, run_git=False)
        assert len(results) == 3
