"""Scoring engine: assigns a deletion-priority score to each environment."""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from killpy.intelligence.git_analyzer import GitAnalyzer
from killpy.models import Environment, GitInfo, ScoredEnvironment

# Marker files that indicate a project lives alongside the environment.
_PROJECT_MARKERS = frozenset(
    {
        "pyproject.toml",
        "setup.py",
        "setup.cfg",
        "requirements.txt",
        "requirements.in",
        "Pipfile",
        "tox.ini",
        ".python-version",
    }
)

# Reference size for normalisation: 500 MB gives a score of ~0.5.
_SIZE_REFERENCE_BYTES = 500 * 1024 * 1024  # 500 MB

# Age in days beyond which an environment scores 1.0 on the age axis.
_MAX_AGE_DAYS = 365


@dataclass
class ScoringWeights:
    """Configurable weights for the scoring formula.

    All weights are normalised internally so they don't need to sum to 1.0.
    """

    size_weight: float = 0.25
    age_weight: float = 0.30
    orphan_weight: float = 0.25
    git_inactivity_weight: float = 0.20


class ScoringService:
    """Compute a deletion-priority score in [0.0, 1.0] for each environment.

    A score closer to **1.0** means the environment is a strong deletion
    candidate; closer to **0.0** means it should be kept.
    """

    def __init__(self, weights: ScoringWeights | None = None) -> None:
        self._w = weights or ScoringWeights()

    # ------------------------------------------------------------------ #
    #  Public API                                                          #
    # ------------------------------------------------------------------ #

    def score(
        self,
        env: Environment,
        git_info: GitInfo | None = None,
    ) -> ScoredEnvironment:
        """Return a :class:`~killpy.models.ScoredEnvironment` for *env*."""
        explanation: list[str] = []

        size_score = self._normalize_size(env.size_bytes)
        explanation.append(f"Size: {env.size_human}")

        age_score, age_days = self._normalize_age(env.last_accessed)
        explanation.append(f"Last accessed {age_days} days ago")

        is_orphan, orphan_score = self._orphan_score(env.path)
        has_project_files = not is_orphan
        explanation.append(
            "No project files found (orphan environment)"
            if is_orphan
            else "Project files found nearby"
        )

        git_score = self._git_inactivity_score(git_info)
        if git_info is None:
            explanation.append("Git status: unknown")
        elif not git_info.is_git_repo:
            explanation.append("No associated git repository")
        elif git_info.is_active:
            explanation.append("Active git repository")
        else:
            explanation.append("Inactive git repository (no recent commits)")

        num_packages = self._count_packages(env.path)

        total_weight = (
            self._w.size_weight
            + self._w.age_weight
            + self._w.orphan_weight
            + self._w.git_inactivity_weight
        )
        raw = (
            self._w.size_weight * size_score
            + self._w.age_weight * age_score
            + self._w.orphan_weight * orphan_score
            + self._w.git_inactivity_weight * git_score
        )
        final_score = raw / total_weight if total_weight > 0 else 0.0

        return ScoredEnvironment(
            env=env,
            score=round(final_score, 4),
            explanation=explanation,
            git_info=git_info,
            has_project_files=has_project_files,
            is_orphan=is_orphan,
            num_packages=num_packages,
        )

    # ------------------------------------------------------------------ #
    #  Internal normalizers                                                #
    # ------------------------------------------------------------------ #

    @staticmethod
    def _normalize_size(size_bytes: int) -> float:
        """Map size to [0, 1] using a sigmoid centred on 500 MB."""
        if size_bytes <= 0:
            return 0.0
        # sigmoid: f(x) = 1 / (1 + e^(-k*(x - x0)))
        # k controls steepness; x0 is the inflection point
        k = 3.0 / _SIZE_REFERENCE_BYTES
        x0 = _SIZE_REFERENCE_BYTES
        return 1.0 / (1.0 + math.exp(-k * (size_bytes - x0)))

    @staticmethod
    def _normalize_age(last_accessed: datetime) -> tuple[float, int]:
        """Return (age_score, age_days) where age_score is linear [0, 1]."""
        now = datetime.now(tz=timezone.utc)
        try:
            la = last_accessed
            if la.tzinfo is None:
                la = la.replace(tzinfo=timezone.utc)
            age_days = max(0, (now - la).days)
        except Exception:  # noqa: BLE001
            return 0.5, 0
        score = min(1.0, age_days / _MAX_AGE_DAYS)
        return score, age_days

    @staticmethod
    def _orphan_score(env_path: Path) -> tuple[bool, float]:
        """Return (is_orphan, score).

        Checks the env dir itself and its immediate parent for project
        marker files.  Orphan = 1.0 (candidate for deletion), not orphan = 0.0.
        """
        search_dirs = [env_path, env_path.parent]
        for d in search_dirs:
            try:
                for marker in _PROJECT_MARKERS:
                    if (d / marker).exists():
                        return False, 0.0
            except OSError:
                pass
        return True, 1.0

    @staticmethod
    def _git_inactivity_score(git_info: GitInfo | None) -> float:
        """Convert git activity into an inactivity score."""
        if git_info is None:
            return 0.5  # unknown → neutral
        if not git_info.is_git_repo:
            return 0.5  # no repo → neutral
        return 0.0 if git_info.is_active else 1.0

    @staticmethod
    def _count_packages(env_path: Path) -> int:
        """Count top-level packages in the environment's site-packages."""
        candidates = [
            env_path / "lib",
            env_path / "Lib" / "site-packages",
        ]
        # lib/pythonX.Y/site-packages
        lib = env_path / "lib"
        if lib.is_dir():
            try:
                for child in lib.iterdir():
                    if child.name.startswith("python"):
                        sp = child / "site-packages"
                        if sp.is_dir():
                            candidates.append(sp)
            except OSError:
                pass

        for sp in candidates:
            if sp.is_dir():
                try:
                    return sum(1 for _ in sp.iterdir())
                except OSError:
                    pass
        return 0


def score_all(
    envs: list[Environment],
    weights: ScoringWeights | None = None,
    *,
    run_git: bool = True,
) -> list[ScoredEnvironment]:
    """Convenience: score every environment in *envs*.

    Parameters
    ----------
    envs:
        Environments to score.
    weights:
        Optional custom scoring weights.
    run_git:
        When ``True`` (default) runs
        :class:`~killpy.intelligence.git_analyzer.GitAnalyzer`
        on each environment path.
    """
    service = ScoringService(weights)
    results: list[ScoredEnvironment] = []
    for env in envs:
        git_info = GitAnalyzer.analyze(env.path) if run_git else None
        results.append(service.score(env, git_info))
    results.sort(key=lambda se: se.score, reverse=True)
    return results
