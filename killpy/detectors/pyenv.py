"""Detector for pyenv-installed Python versions."""

from __future__ import annotations

import logging
import platform
from datetime import datetime
from pathlib import Path

from killpy.detectors.base import AbstractDetector
from killpy.files import get_total_size
from killpy.models import Environment

logger = logging.getLogger(__name__)


def _pyenv_versions_root() -> Path:
    """Return the pyenv versions directory for the current platform."""
    home = Path.home()
    if platform.system() == "Windows":  # pragma: no cover
        win_root = home / ".pyenv" / "pyenv-win" / "versions"  # pragma: no cover
        if win_root.exists():  # pragma: no cover
            return win_root  # pragma: no cover
    return home / ".pyenv" / "versions"


class PyenvDetector(AbstractDetector):
    """Detects Python installations managed by pyenv.

    The scan *path* argument is ignored because pyenv stores versions in
    ``~/.pyenv/versions`` (or ``~/.pyenv/pyenv-win/versions`` on Windows).
    """

    name = "pyenv"

    def can_handle(self) -> bool:
        return _pyenv_versions_root().exists()

    def detect(self, path: Path) -> list[Environment]:  # noqa: ARG002
        versions_root = _pyenv_versions_root()
        if not versions_root.exists():
            return []

        envs: list[Environment] = []
        try:
            for version_dir in versions_root.iterdir():
                if not version_dir.is_dir():
                    continue
                try:
                    stat = version_dir.stat()
                    size = get_total_size(version_dir)
                    envs.append(
                        Environment(
                            path=version_dir,
                            name=version_dir.name,
                            type="pyenv",
                            last_accessed=datetime.fromtimestamp(stat.st_mtime),
                            size_bytes=size,
                        )
                    )
                except (FileNotFoundError, OSError) as exc:
                    logger.debug("Skipping pyenv version %s: %s", version_dir, exc)
        except OSError as exc:
            logger.error("Cannot inspect pyenv versions root: %s", exc)
            return []

        envs.sort(key=lambda e: e.size_bytes, reverse=True)
        return envs
