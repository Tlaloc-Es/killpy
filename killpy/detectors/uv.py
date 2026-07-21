"""Detector for disk space owned by uv itself (tool envs and Pythons)."""

from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from pathlib import Path

from killpy.detectors.base import AbstractDetector
from killpy.files import get_total_size
from killpy.models import Environment

logger = logging.getLogger(__name__)


def _uv_data_dir() -> Path:
    xdg = os.environ.get("XDG_DATA_HOME")
    base = Path(xdg) if xdg else Path.home() / ".local" / "share"
    return base / "uv"


def _uv_tools_dir() -> Path:
    override = os.environ.get("UV_TOOL_DIR")
    return Path(override) if override else _uv_data_dir() / "tools"


def _uv_python_dir() -> Path:
    override = os.environ.get("UV_PYTHON_INSTALL_DIR")
    return Path(override) if override else _uv_data_dir() / "python"


class UvDetector(AbstractDetector):
    """Detects environments managed by uv itself.

    Covers:

    * Tool environments installed with ``uv tool install`` (uv's pipx
      equivalent), stored under ``~/.local/share/uv/tools``.  Marked
      ``managed_by="uv"`` so deletion goes through ``uv tool uninstall``
      and the ``~/.local/bin`` shims are cleaned up too.
    * Python versions installed with ``uv python install``, stored under
      ``~/.local/share/uv/python``.

    ``UV_TOOL_DIR``, ``UV_PYTHON_INSTALL_DIR`` and ``XDG_DATA_HOME`` are
    honoured.  Project virtualenvs created by ``uv venv`` / ``uv sync``
    are regular ``pyvenv.cfg`` environments reported by
    :class:`~killpy.detectors.venv.VenvDetector`, and the global uv cache
    is reported by the cache detector.  The scan *path* argument is
    ignored.
    """

    name = "uv"
    required_tool = "uv"  # tool-or-directory contract

    def _candidate_dirs(self) -> tuple[Path, ...]:
        # ...or one of its tool/python data directories exists.
        return (_uv_tools_dir(), _uv_python_dir())

    def detect(self, path: Path) -> list[Environment]:  # noqa: ARG002
        envs: list[Environment] = []
        envs.extend(self._scan_dir(_uv_tools_dir(), managed_by="uv"))
        envs.extend(self._scan_dir(_uv_python_dir(), managed_by=None))
        return envs

    @staticmethod
    def _scan_dir(root: Path, managed_by: str | None) -> list[Environment]:
        if not root.exists():
            return []
        envs: list[Environment] = []
        try:
            for env_dir in root.iterdir():
                if not env_dir.is_dir():
                    continue
                try:
                    stat = env_dir.stat()
                    size = get_total_size(env_dir)
                    mtime = datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc)
                    envs.append(
                        Environment(
                            path=env_dir,
                            name=env_dir.name,
                            type="uv",
                            last_modified=mtime,
                            size_bytes=size,
                            managed_by=managed_by,
                        )
                    )
                except (FileNotFoundError, OSError) as exc:
                    logger.debug("Skipping uv entry %s: %s", env_dir, exc)
        except OSError as exc:
            logger.error("Cannot inspect uv dir %s: %s", root, exc)
        return envs
