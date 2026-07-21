"""Detector for pyenv-installed Python versions."""

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


def _pyenv_root() -> Path:
    """Return the pyenv root directory, honouring ``PYENV_ROOT``."""
    override = os.environ.get("PYENV_ROOT")
    if override:
        return Path(override).expanduser()
    return Path.home() / ".pyenv"


def _pyenv_versions_root() -> Path:
    """Return the pyenv versions directory for the current platform."""
    root = _pyenv_root()
    if platform.system() == "Windows":  # pragma: no cover
        win_root = root / "pyenv-win" / "versions"  # pragma: no cover
        if win_root.exists():  # pragma: no cover
            return win_root  # pragma: no cover
    return root / "versions"


class PyenvDetector(AbstractDetector):
    """Detects Python installations managed by pyenv.

    The scan *path* argument is ignored because pyenv stores versions in
    ``~/.pyenv/versions`` (or ``~/.pyenv/pyenv-win/versions`` on Windows).
    """

    name = "pyenv"

    def _candidate_dirs(self) -> tuple[Path, ...]:
        # Contract: directory — applies only if pyenv's versions directory exists.
        return (_pyenv_versions_root(),)

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
                    mtime = datetime.fromtimestamp(
                        stat.st_mtime,
                        tz=timezone.utc,
                    )
                    envs.append(
                        Environment(
                            path=version_dir,
                            name=version_dir.name,
                            type="pyenv",
                            last_modified=mtime,
                            size_bytes=size,
                        )
                    )
                except (FileNotFoundError, OSError) as exc:
                    logger.debug("Skipping pyenv version %s: %s", version_dir, exc)
        except OSError as exc:
            logger.error("Cannot inspect pyenv versions root: %s", exc)
            return []

        return envs
