"""Detector for Hatch-managed environments."""

from __future__ import annotations

import logging
import platform
import shutil
from datetime import datetime, timezone
from pathlib import Path

from killpy.detectors.base import AbstractDetector
from killpy.files import get_total_size
from killpy.models import Environment

logger = logging.getLogger(__name__)


def _hatch_envs_root() -> Path:
    """Return the default hatch environments directory for the current OS."""
    if platform.system() == "Windows":  # pragma: no cover
        local_app = (
            Path.home() / "AppData" / "Local" / "hatch" / "env"
        )  # pragma: no cover
        if local_app.exists():  # pragma: no cover
            return local_app  # pragma: no cover
    # Linux / macOS
    return Path.home() / ".local" / "share" / "hatch" / "env"


class HatchDetector(AbstractDetector):
    """Detects Hatch-managed environments (stored in the global hatch env dir).

    The scan *path* argument is ignored.
    """

    name = "hatch"

    def can_handle(self) -> bool:
        return shutil.which("hatch") is not None or _hatch_envs_root().exists()

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
                            stat.st_mtime, tz=timezone.utc,
                        )
                        envs.append(
                            Environment(
                                path=env_dir,
                                name=f"{project_dir.name}/{env_dir.name}",
                                type="hatch",
                                last_accessed=mtime,
                                size_bytes=size,
                            )
                        )
                    except (FileNotFoundError, OSError) as exc:
                        logger.debug("Skipping hatch env %s: %s", env_dir, exc)
        except OSError as exc:
            logger.error("Cannot inspect hatch envs root: %s", exc)
            return []

        envs.sort(key=lambda e: e.size_bytes, reverse=True)
        return envs
