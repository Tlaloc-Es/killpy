"""Unit tests for ``killpy.intelligence.suggestions``."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

from killpy.intelligence.suggestions import (
    _HIGH_AGE_NO_PROJECT_THRESHOLD,
    _HIGH_AGE_ORPHAN_THRESHOLD,
    _LOW_AGE_THRESHOLD,
    _MEDIUM_AGE_THRESHOLD,
    SuggestionEngine,
)
from killpy.models import Environment, GitInfo, ScoredEnvironment

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_SMALL = 512 * 1024  # 512 KB
_MEDIUM = 5 * 1024 * 1024  # 5 MB
_LARGE = 200 * 1024 * 1024  # 200 MB


def _env(
    path: Path | None = None, days_old: int = 30, size: int = _LARGE
) -> Environment:
    return Environment(
        path=path or Path("/fake/env"),
        name="env",
        type="venv",
        last_accessed=datetime.now(tz=timezone.utc) - timedelta(days=days_old),
        size_bytes=size,
        managed_by=None,
    )


def _scored(
    days_old: int = 30,
    score: float = 0.3,
    is_orphan: bool = False,
    git_info: GitInfo | None = None,
    path: Path | None = None,
    size: int = _LARGE,
) -> ScoredEnvironment:
    env = _env(path=path, days_old=days_old, size=size)
    return ScoredEnvironment(
        env=env,
        score=score,
        explanation=[],
        git_info=git_info,
        has_project_files=not is_orphan,
        is_orphan=is_orphan,
        num_packages=0,
    )


_ACTIVE_GIT = GitInfo(is_git_repo=True, is_active=True)
_INACTIVE_GIT = GitInfo(is_git_repo=True, is_active=False)


# ---------------------------------------------------------------------------
# HIGH category
# ---------------------------------------------------------------------------


class TestHighCategory:
    def test_orphan_old_enough_is_high(self) -> None:
        engine = SuggestionEngine()
        suggestion = engine.classify(
            _scored(is_orphan=True, days_old=_HIGH_AGE_ORPHAN_THRESHOLD, size=_SMALL)
        )
        assert suggestion.category == "HIGH"

    def test_orphan_very_old_is_high_regardless_of_size(self) -> None:
        engine = SuggestionEngine()
        for size in (_SMALL, _MEDIUM, _LARGE):
            suggestion = engine.classify(
                _scored(
                    is_orphan=True,
                    days_old=_HIGH_AGE_ORPHAN_THRESHOLD + 1,
                    size=size,
                )
            )
            assert suggestion.category == "HIGH", f"size={size}"

    def test_no_project_files_very_old_is_high(self) -> None:
        engine = SuggestionEngine()
        suggestion = engine.classify(
            _scored(
                is_orphan=True,
                days_old=_HIGH_AGE_NO_PROJECT_THRESHOLD,
                size=_SMALL,
            )
        )
        assert suggestion.category == "HIGH"

    def test_orphan_below_age_threshold_not_high(self) -> None:
        engine = SuggestionEngine()
        suggestion = engine.classify(
            _scored(
                is_orphan=True,
                days_old=_HIGH_AGE_ORPHAN_THRESHOLD - 1,
                size=_LARGE,
            )
        )
        assert suggestion.category != "HIGH"

    def test_active_git_old_orphan_is_still_high(self) -> None:
        """ORPHAN + OLD must ALWAYS be HIGH — active git does not override this rule."""
        engine = SuggestionEngine()
        suggestion = engine.classify(
            _scored(
                is_orphan=True,
                days_old=_HIGH_AGE_ORPHAN_THRESHOLD + 50,
                size=_LARGE,
                git_info=_ACTIVE_GIT,
            )
        )
        assert suggestion.category == "HIGH"


# ---------------------------------------------------------------------------
# MEDIUM category
# ---------------------------------------------------------------------------


class TestMediumCategory:
    def test_old_non_orphan_env_is_medium(self) -> None:
        engine = SuggestionEngine()
        suggestion = engine.classify(
            _scored(days_old=_MEDIUM_AGE_THRESHOLD, is_orphan=False, size=_LARGE)
        )
        assert suggestion.category == "MEDIUM"

    def test_slightly_above_medium_threshold_is_medium(self) -> None:
        engine = SuggestionEngine()
        suggestion = engine.classify(
            _scored(days_old=_MEDIUM_AGE_THRESHOLD + 10, size=_SMALL)
        )
        assert suggestion.category == "MEDIUM"

    def test_active_git_overrides_to_low(self) -> None:
        engine = SuggestionEngine()
        suggestion = engine.classify(
            _scored(
                days_old=_MEDIUM_AGE_THRESHOLD + 10, git_info=_ACTIVE_GIT, size=_LARGE
            )
        )
        assert suggestion.category == "LOW"


# ---------------------------------------------------------------------------
# LOW category
# ---------------------------------------------------------------------------


class TestLowCategory:
    def test_recently_used_with_active_git_is_low(self) -> None:
        engine = SuggestionEngine()
        suggestion = engine.classify(
            _scored(days_old=5, git_info=_ACTIVE_GIT, size=_LARGE)
        )
        assert suggestion.category == "LOW"

    def test_recently_used_no_git_is_low(self) -> None:
        engine = SuggestionEngine()
        suggestion = engine.classify(_scored(days_old=5, size=_LARGE))
        assert suggestion.category == "LOW"

    def test_age_just_below_threshold_is_low(self) -> None:
        engine = SuggestionEngine()
        suggestion = engine.classify(
            _scored(days_old=_LOW_AGE_THRESHOLD - 1, size=_LARGE)
        )
        assert suggestion.category == "LOW"

    def test_active_git_always_low_regardless_of_age(self) -> None:
        engine = SuggestionEngine()
        for days in (5, 100, 200, 400):
            suggestion = engine.classify(
                _scored(days_old=days, git_info=_ACTIVE_GIT, size=_SMALL)
            )
            assert suggestion.category == "LOW", f"days={days}"


# ---------------------------------------------------------------------------
# classify_all
# ---------------------------------------------------------------------------


class TestClassifyAll:
    def test_sorted_high_first(self) -> None:
        engine = SuggestionEngine()
        envs = [
            _scored(days_old=5, score=0.1, size=_LARGE),
            _scored(
                is_orphan=True,
                days_old=_HIGH_AGE_ORPHAN_THRESHOLD + 1,
                size=_LARGE,
            ),
            _scored(days_old=_MEDIUM_AGE_THRESHOLD + 5, score=0.2, size=_LARGE),
        ]
        suggestions = engine.classify_all(envs)
        categories = [s.category for s in suggestions]
        assert categories.index("HIGH") < categories.index("MEDIUM")
        assert categories.index("MEDIUM") < categories.index("LOW")

    def test_empty_list_returns_empty(self) -> None:
        engine = SuggestionEngine()
        assert engine.classify_all([]) == []

    def test_all_get_classified(self) -> None:
        engine = SuggestionEngine()
        envs = [_scored() for _ in range(5)]
        result = engine.classify_all(envs)
        assert len(result) == 5


# ---------------------------------------------------------------------------
# Suggestion content
# ---------------------------------------------------------------------------


class TestSuggestionContent:
    def test_reasons_list_populated(self) -> None:
        engine = SuggestionEngine()
        suggestion = engine.classify(
            _scored(is_orphan=True, days_old=_HIGH_AGE_ORPHAN_THRESHOLD, size=_LARGE)
        )
        assert len(suggestion.reasons) > 0

    def test_orphan_reason_present_for_high(self) -> None:
        engine = SuggestionEngine()
        suggestion = engine.classify(
            _scored(is_orphan=True, days_old=_HIGH_AGE_ORPHAN_THRESHOLD, size=_SMALL)
        )
        assert any("orphan" in r.lower() for r in suggestion.reasons)

    def test_recommended_action_set(self) -> None:
        engine = SuggestionEngine()
        for scored in [
            _scored(is_orphan=True, days_old=_HIGH_AGE_ORPHAN_THRESHOLD, size=_LARGE),
            _scored(days_old=_MEDIUM_AGE_THRESHOLD + 10, score=0.2, size=_LARGE),
            _scored(days_old=5, size=_LARGE),
        ]:
            suggestion = engine.classify(scored)
            assert suggestion.recommended_action

    def test_score_preserved(self) -> None:
        engine = SuggestionEngine()
        scored = _scored(score=0.67)
        suggestion = engine.classify(scored)
        assert suggestion.score == 0.67

    def test_no_raw_scores_in_reasons(self) -> None:
        """Reasons should be human-readable, not contain raw numeric scores."""
        engine = SuggestionEngine()
        for scored in [
            _scored(is_orphan=True, days_old=_HIGH_AGE_ORPHAN_THRESHOLD, size=_LARGE),
            _scored(days_old=_MEDIUM_AGE_THRESHOLD + 10, size=_LARGE),
            _scored(days_old=5, size=_SMALL),
        ]:
            for reason in engine.classify(scored).reasons:
                assert "score" not in reason.lower(), f"Found raw score in: {reason!r}"

    def test_expected_scenarios(self) -> None:
        """Mandatory expected behavior from the spec."""
        engine = SuggestionEngine()

        # orphan + 400 days → HIGH
        s = engine.classify(_scored(is_orphan=True, days_old=400))
        assert s.category == "HIGH", "orphan + 400 days must be HIGH"

        # orphan + 700 days → HIGH
        s = engine.classify(_scored(is_orphan=True, days_old=700))
        assert s.category == "HIGH", "orphan + 700 days must be HIGH"

        # project + 150 days → MEDIUM
        s = engine.classify(_scored(is_orphan=False, days_old=150))
        assert s.category == "MEDIUM", "project + 150 days must be MEDIUM"

        # active + 5 days → LOW
        s = engine.classify(_scored(git_info=_ACTIVE_GIT, days_old=5))
        assert s.category == "LOW", "active + 5 days must be LOW"
