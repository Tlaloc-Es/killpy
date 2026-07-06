"""Detector for Poetry virtual environments (global cache)."""

from __future__ import annotations

import logging
import os
import platform
from datetime import datetime, timezone
from pathlib import Path

from killpy.detectors.base import AbstractDetector
from killpy.files import get_total_size
from killpy.models import Environment

logger = logging.getLogger(__name__)


def _poetry_venvs_dir() -> Path:
    """Return Poetry's virtualenvs directory for the current platform.

    Honours ``POETRY_CACHE_DIR`` and ``XDG_CACHE_HOME``; uses the
    platform-specific cache location on macOS and Windows.
    """
    override = os.environ.get("POETRY_CACHE_DIR")
    if override:
        return Path(override).expanduser() / "virtualenvs"
    system = platform.system()
    if system == "Windows":  # pragma: no cover
        return (
            Path.home() / "AppData" / "Local" / "pypoetry" / "Cache" / "virtualenvs"
        )  # pragma: no cover
    if system == "Darwin":
        return Path.home() / "Library" / "Caches" / "pypoetry" / "virtualenvs"
    xdg = os.environ.get("XDG_CACHE_HOME")
    base = Path(xdg) if xdg else Path.home() / ".cache"
    return base / "pypoetry" / "virtualenvs"


class PoetryDetector(AbstractDetector):
    """Detects Poetry-managed virtual environments stored in the global cache.

    The scan *path* argument is intentionally ignored – Poetry always stores
    its virtualenvs in a user-level cache directory regardless of the project
    location.
    """

    name = "poetry"

    def can_handle(self) -> bool:
        return _poetry_venvs_dir().exists()

    def detect(self, path: Path) -> list[Environment]:  # noqa: ARG002
        venvs_dir = _poetry_venvs_dir()
        if not venvs_dir.exists():
            return []

        envs: list[Environment] = []
        try:
            for venv_path in venvs_dir.iterdir():
                if not venv_path.is_dir():
                    continue
                try:
                    stat = venv_path.stat()
                    size = get_total_size(venv_path)
                    mtime = datetime.fromtimestamp(
                        stat.st_mtime,
                        tz=timezone.utc,
                    )
                    envs.append(
                        Environment(
                            path=venv_path,
                            name=venv_path.name,
                            type="poetry",
                            last_accessed=mtime,
                            size_bytes=size,
                        )
                    )
                except (FileNotFoundError, OSError) as exc:
                    logger.debug(
                        "Skipping inaccessible poetry env %s: %s", venv_path, exc
                    )

        except OSError as exc:
            logger.error("Cannot inspect poetry virtualenvs dir: %s", exc)
            return []

        return envs
