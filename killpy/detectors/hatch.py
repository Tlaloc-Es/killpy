"""Detector for Hatch-managed environments."""

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


def _hatch_envs_root() -> Path:
    """Return the hatch environments directory for the current OS.

    Honours ``HATCH_DATA_DIR`` and ``XDG_DATA_HOME``; uses the
    platform-specific data location on macOS and Windows.
    """
    override = os.environ.get("HATCH_DATA_DIR")
    if override:
        return Path(override).expanduser() / "env"
    system = platform.system()
    if system == "Windows":  # pragma: no cover
        return Path.home() / "AppData" / "Local" / "hatch" / "env"  # pragma: no cover
    if system == "Darwin":
        return Path.home() / "Library" / "Application Support" / "hatch" / "env"
    xdg = os.environ.get("XDG_DATA_HOME")
    base = Path(xdg) if xdg else Path.home() / ".local" / "share"
    return base / "hatch" / "env"


class HatchDetector(AbstractDetector):
    """Detects Hatch-managed environments (stored in the global hatch env dir).

    The scan *path* argument is ignored.
    """

    name = "hatch"
    required_tool = "hatch"  # tool-or-directory contract

    def _candidate_dirs(self) -> tuple[Path, ...]:
        # ...or its global environments directory exists.
        return (_hatch_envs_root(),)

    def detect(self, path: Path) -> list[Environment]:  # noqa: ARG002
        envs_root = _hatch_envs_root()
        if not envs_root.exists():
            return []

        envs: list[Environment] = []
        try:
            # Hatch nests envs: <root>/<project>/<env-name>/
            for project_dir in envs_root.iterdir():
                if not project_dir.is_dir():
                    continue
                for env_dir in project_dir.iterdir():
                    if not env_dir.is_dir():
                        continue
                    try:
                        stat = env_dir.stat()
                        size = get_total_size(env_dir)
                        mtime = datetime.fromtimestamp(
                            stat.st_mtime,
                            tz=timezone.utc,
                        )
                        envs.append(
                            Environment(
                                path=env_dir,
                                name=f"{project_dir.name}/{env_dir.name}",
                                type="hatch",
                                last_modified=mtime,
                                size_bytes=size,
                            )
                        )
                    except (FileNotFoundError, OSError) as exc:
                        logger.debug("Skipping hatch env %s: %s", env_dir, exc)
        except OSError as exc:
            logger.error("Cannot inspect hatch envs root: %s", exc)
            return []

        return envs
