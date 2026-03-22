"""Detector for local ``.venv`` directories and ``pyvenv.cfg`` files."""

from __future__ import annotations

import logging
import os
from datetime import datetime
from pathlib import Path

from killpy.detectors.base import AbstractDetector
from killpy.files import get_total_size
from killpy.models import Environment

logger = logging.getLogger(__name__)

# Directory names that should never be walked into when scanning.
_EXCLUDED_DIRS: frozenset[str] = frozenset(
    {
        ".git",
        ".hg",
        ".svn",
        "node_modules",
        ".tox",
        ".nox",
        ".mypy_cache",
        ".pytest_cache",
        "__pycache__",
        ".ruff_cache",
        "dist",
        "build",
    }
)


def _iter_dirs_named(root: Path, target: str):
    """Yield every directory named *target* under *root*, pruning excluded dirs."""
    for current_root, directories, _ in os.walk(root, topdown=True):
        directories[:] = [d for d in directories if d not in _EXCLUDED_DIRS]
        if target in directories:
            yield Path(current_root) / target


def _iter_files_named(root: Path, filename: str):
    """Yield every file named *filename* under *root*, pruning excluded dirs."""
    for current_root, directories, files in os.walk(root, topdown=True):
        directories[:] = [d for d in directories if d not in _EXCLUDED_DIRS]
        if filename in files:
            yield Path(current_root) / filename


class VenvDetector(AbstractDetector):
    """Detects ``.venv`` directories (explicit virtualenv convention).

    Also detects any directory that contains a ``pyvenv.cfg`` file at its
    root, which covers virtualenvs created with the standard library
    ``venv`` module regardless of their name.
    """

    name = "venv"

    def can_handle(self) -> bool:
        # Always applicable – pure filesystem scan.
        return True

    def detect(self, path: Path) -> list[Environment]:
        seen: set[Path] = set()
        envs: list[Environment] = []

        # 1. Named ".venv" directories
        for dir_path in _iter_dirs_named(path, ".venv"):
            try:
                resolved = dir_path.resolve(strict=True)
                if resolved in seen:
                    continue
                seen.add(resolved)
                envs.append(_make_env(dir_path, ".venv"))
            except (FileNotFoundError, OSError) as exc:
                logger.debug("Skipping %s: %s", dir_path, exc)

        # 2. Directories that contain pyvenv.cfg (catches non-.venv names)
        for cfg_file in _iter_files_named(path, "pyvenv.cfg"):
            venv_dir = cfg_file.parent
            try:
                resolved = venv_dir.resolve(strict=True)
                if resolved in seen:
                    continue
                seen.add(resolved)
                envs.append(_make_env(venv_dir, "pyvenv.cfg"))
            except (FileNotFoundError, OSError) as exc:
                logger.debug("Skipping %s: %s", venv_dir, exc)

        envs.sort(key=lambda e: e.size_bytes, reverse=True)
        return envs


# ------------------------------------------------------------------ #
#  Private helpers                                                     #
# ------------------------------------------------------------------ #


def _make_env(dir_path: Path, tag: str) -> Environment:
    stat = dir_path.stat()
    size = get_total_size(dir_path)
    return Environment(
        path=dir_path,
        name=str(dir_path),
        type=tag,
        last_accessed=datetime.fromtimestamp(stat.st_mtime),
        size_bytes=size,
    )
