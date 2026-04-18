"""killpy.intelligence – smart scoring, git analysis, and suggestions."""

from __future__ import annotations

from killpy.intelligence.git_analyzer import GitAnalyzer
from killpy.intelligence.scoring import ScoringService, ScoringWeights, score_all
from killpy.intelligence.suggestions import SuggestionEngine
from killpy.intelligence.tracker import UsageTracker
from killpy.models import (
    Environment,
    GitInfo,
    ScanRecord,
    ScoredEnvironment,
    Suggestion,
)

__all__ = [
    "GitAnalyzer",
    "GitInfo",
    "ScoringService",
    "ScoringWeights",
    "ScoredEnvironment",
    "SuggestionEngine",
    "Suggestion",
    "UsageTracker",
    "ScanRecord",
    "score_all",
    "analyze_environments",
]


def analyze_environments(
    envs: list[Environment],
    weights: ScoringWeights | None = None,
    *,
    run_git: bool = True,
) -> list[Suggestion]:
    """Full intelligence pipeline: git → score → suggest.

    Parameters
    ----------
    envs:
        Environments returned by :class:`~killpy.scanner.Scanner`.
    weights:
        Optional custom :class:`ScoringWeights`.
    run_git:
        When ``True`` (default) enriches each environment with git data.

    Returns
    -------
    list[Suggestion]
        Suggestions sorted by category (HIGH → MEDIUM → LOW) then score.
    """
    scored = score_all(envs, weights, run_git=run_git)
    engine = SuggestionEngine()
    return engine.classify_all(scored)
