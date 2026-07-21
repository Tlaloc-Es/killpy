"""Detector for Pipenv virtual environments (stored in a global dir)."""

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


def _pipenv_venvs_root() -> Path:
    """Return the pipenv virtualenvs directory, honouring ``WORKON_HOME``."""
    override = os.environ.get("WORKON_HOME")
    if override:
        return Path(override).expanduser()
    if platform.system() == "Windows":  # pragma: no cover
        return Path.home() / ".virtualenvs"  # pragma: no cover
    return Path.home() / ".local" / "share" / "virtualenvs"


class PipenvDetector(AbstractDetector):
    """Detects Pipenv-managed virtual environments.

    Pipenv stores all virtualenvs in a single user-level directory
    (``~/.local/share/virtualenvs`` on Linux/macOS).  The scan *path*
    argument is ignored.
    """

    name = "pipenv"
    required_tool = "pipenv"  # tool-or-directory contract

    def _candidate_dirs(self) -> tuple[Path, ...]:
        # ...or its global virtualenvs directory exists.
        return (_pipenv_venvs_root(),)

    def detect(self, path: Path) -> list[Environment]:  # noqa: ARG002
        venvs_root = _pipenv_venvs_root()
        if not venvs_root.exists():
            return []

        envs: list[Environment] = []
        try:
            for venv_path in venvs_root.iterdir():
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
                            type="pipenv",
                            last_modified=mtime,
                            size_bytes=size,
                        )
                    )
                except (FileNotFoundError, OSError) as exc:
                    logger.debug("Skipping pipenv venv %s: %s", venv_path, exc)
        except OSError as exc:
            logger.error("Cannot inspect pipenv venvs root: %s", exc)
            return []

        return envs
