"""Detector for Poetry virtual environments (global cache)."""

from __future__ import annotations

import logging
import platform
from datetime import datetime, timezone
from pathlib import Path

from killpy.detectors.base import AbstractDetector
from killpy.files import get_total_size
from killpy.models import Environment

logger = logging.getLogger(__name__)


def _poetry_venvs_dir() -> Path:
    if platform.system() == "Windows":  # pragma: no cover
        return (
            Path.home() / "AppData" / "Local" / "pypoetry" / "virtualenvs"
        )  # pragma: no cover
    return Path.home() / ".cache" / "pypoetry" / "virtualenvs"


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
                        stat.st_mtime, tz=timezone.utc,
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

        envs.sort(key=lambda e: e.size_bytes, reverse=True)
        return envs
