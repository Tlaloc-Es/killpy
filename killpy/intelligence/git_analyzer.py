"""Git repository analysis for environment activity detection."""

from __future__ import annotations

import logging
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from killpy.models import GitInfo

logger = logging.getLogger(__name__)

_ACTIVE_THRESHOLD_DAYS = 60


class GitAnalyzer:
    """Detect git repos and their activity level.

    All methods return safe defaults when git is not installed or any
    subprocess/filesystem operation fails.
    """

    # ------------------------------------------------------------------ #
    #  Filesystem helpers (no subprocess)                                  #
    # ------------------------------------------------------------------ #

    @staticmethod
    def find_repo_root(path: Path) -> Path | None:
        """Walk *path* upwards looking for a ``.git`` directory.

        Returns the directory that contains ``.git``, or ``None`` if not
        found before reaching the filesystem root.
        """
        current = path.resolve()
        while True:
            if (current / ".git").exists():
                return current
            parent = current.parent
            if parent == current:
                return None
            current = parent

    @staticmethod
    def is_git_repo(path: Path) -> bool:
        """Return ``True`` when *path* (or any ancestor) is inside a git repo."""
        return GitAnalyzer.find_repo_root(path) is not None

    # ------------------------------------------------------------------ #
    #  Subprocess helpers                                                  #
    # ------------------------------------------------------------------ #

    @staticmethod
    def get_last_commit(repo_root: Path) -> datetime | None:
        """Return the UTC timestamp of the most recent commit, or ``None``."""
        try:
            result = subprocess.run(
                ["git", "-C", str(repo_root), "log", "-1", "--format=%ct"],
                check=False,
                capture_output=True,
                text=True,
                timeout=10,
            )
        except (FileNotFoundError, subprocess.TimeoutExpired, OSError) as exc:
            logger.debug("git log failed for %s: %s", repo_root, exc)
            return None

        raw = result.stdout.strip()
        if not raw or result.returncode != 0:
            return None

        try:
            return datetime.fromtimestamp(int(raw), tz=timezone.utc)
        except (ValueError, OSError) as exc:
            logger.debug("Could not parse git timestamp %r: %s", raw, exc)
            return None

    @staticmethod
    def is_active_repo(
        repo_root: Path, threshold_days: int = _ACTIVE_THRESHOLD_DAYS
    ) -> bool:
        """Return ``True`` when the repo had a commit within *threshold_days*."""
        last = GitAnalyzer.get_last_commit(repo_root)
        if last is None:
            return False
        age_days = (datetime.now(tz=timezone.utc) - last).days
        return age_days < threshold_days

    # ------------------------------------------------------------------ #
    #  Public orchestrator                                                 #
    # ------------------------------------------------------------------ #

    @staticmethod
    def analyze(env_path: Path) -> GitInfo:
        """Run full git analysis for the environment at *env_path*.

        Returns a :class:`~killpy.models.GitInfo` with safe defaults when
        git is not installed or no repo is found.
        """
        if shutil.which("git") is None:
            return GitInfo(is_git_repo=False, is_active=False)

        repo_root = GitAnalyzer.find_repo_root(env_path)
        if repo_root is None:
            return GitInfo(is_git_repo=False, is_active=False)

        last_commit = GitAnalyzer.get_last_commit(repo_root)
        is_active = False
        if last_commit is not None:
            age_days = (datetime.now(tz=timezone.utc) - last_commit).days
            is_active = age_days < _ACTIVE_THRESHOLD_DAYS

        return GitInfo(
            is_git_repo=True,
            is_active=is_active,
            last_commit=last_commit,
            repo_root=repo_root,
        )
