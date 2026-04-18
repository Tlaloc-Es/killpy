"""Suggestion engine: classifies scored environments into action categories."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal

from killpy.models import ScoredEnvironment, Suggestion

# Age thresholds in days.
_HIGH_AGE_ORPHAN_THRESHOLD = 180  # orphan + age >= this → HIGH
_HIGH_AGE_NO_PROJECT_THRESHOLD = 365  # no project files + age >= this → HIGH
_MEDIUM_AGE_THRESHOLD = 120  # age >= this → MEDIUM
_LOW_AGE_THRESHOLD = 120  # age < this → LOW

_ACTION_HIGH = "Delete — unused and orphaned"
_ACTION_MEDIUM = "Review — possibly unused"
_ACTION_LOW_ACTIVE = "Keep — actively used"
_ACTION_LOW = "Keep"


class SuggestionEngine:
    """Classify a :class:`~killpy.models.ScoredEnvironment` into a recommendation.

    Categories:

    * ``"HIGH"`` — safe to delete (age and orphan status dominate)
    * ``"MEDIUM"`` — worth reviewing
    * ``"LOW"`` — keep

    Age and orphan status are the primary signals.  Size is kept only for
    sorting (via ``score``); it does NOT affect category assignment.
    """

    def classify(self, scored: ScoredEnvironment) -> Suggestion:
        """Return a :class:`~killpy.models.Suggestion` for *scored*."""
        reasons: list[str] = []
        age_days = self._age_days(scored)

        category, action = self._determine_category(scored, age_days, reasons)

        return Suggestion(
            env_path=scored.env.path,
            score=scored.score,
            category=category,
            reasons=reasons,
            recommended_action=action,
        )

    def classify_all(self, scored_envs: list[ScoredEnvironment]) -> list[Suggestion]:
        """Classify every environment and return sorted suggestions (HIGH first)."""
        order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
        suggestions = [self.classify(se) for se in scored_envs]
        suggestions.sort(key=lambda s: (order[s.category], -s.score))
        return suggestions

    # ------------------------------------------------------------------ #
    #  Internal helpers                                                    #
    # ------------------------------------------------------------------ #

    @staticmethod
    def _age_days(scored: ScoredEnvironment) -> int:
        """Return age in days based on env.last_accessed."""
        la = scored.env.last_accessed
        if la.tzinfo is None:
            la = la.replace(tzinfo=timezone.utc)
        return max(0, (datetime.now(tz=timezone.utc) - la).days)

    @staticmethod
    def _determine_category(
        scored: ScoredEnvironment,
        age_days: int,
        reasons: list[str],
    ) -> tuple[Literal["HIGH", "MEDIUM", "LOW"], str]:
        is_orphan = scored.is_orphan
        has_project_files = scored.has_project_files
        is_active_git = (
            scored.git_info is not None
            and scored.git_info.is_git_repo
            and scored.git_info.is_active
        )

        # ── Rule 1: HIGH — orphan and stale ────────────────────────────────────
        if is_orphan and age_days >= _HIGH_AGE_ORPHAN_THRESHOLD:
            reasons.append("Orphan — no project files found nearby")
            reasons.append(f"Not used in {age_days} days")
            return "HIGH", _ACTION_HIGH

        # ── Rule 1b: HIGH — no project files and very old ──────────────────────
        if not has_project_files and age_days >= _HIGH_AGE_NO_PROJECT_THRESHOLD:
            reasons.append("Orphan — no project files found nearby")
            reasons.append(f"Not used in {age_days} days")
            return "HIGH", _ACTION_HIGH

        # ── Rule 2: LOW — active git or very recent ─────────────────────────────
        if is_active_git or age_days < _LOW_AGE_THRESHOLD:
            if is_active_git:
                reasons.append("Active git repository")
            if age_days < _LOW_AGE_THRESHOLD:
                reasons.append(f"Recently used ({age_days} days ago)")
            action = _ACTION_LOW_ACTIVE if is_active_git else _ACTION_LOW
            return "LOW", action

        # ── Rule 3: MEDIUM — moderately old ────────────────────────────────────
        if age_days >= _MEDIUM_AGE_THRESHOLD:
            if is_orphan:
                reasons.append("Orphan — no project files found nearby")
            reasons.append(f"Not used in {age_days} days")
            if (
                scored.git_info is not None
                and scored.git_info.is_git_repo
                and not scored.git_info.is_active
            ):
                reasons.append("Associated git repo has no recent commits")
            return "MEDIUM", _ACTION_MEDIUM

        # ── Rule 4: FALLBACK → LOW ──────────────────────────────────────────────
        if is_active_git:
            reasons.append("Active git repository")
        return "LOW", _ACTION_LOW
