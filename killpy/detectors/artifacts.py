"""Detector for Python build artifacts (dist/, build/, *.egg-info/, *.dist-info/)."""

from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from pathlib import Path

from killpy.detectors.base import AbstractDetector
from killpy.files import get_total_size
from killpy.models import Environment

logger = logging.getLogger(__name__)

_PRUNED: frozenset[str] = frozenset({".git", ".hg", ".svn", "node_modules"})
# Environment internals are not build artifacts: every installed package has
# a ``site-packages/*.dist-info`` directory whose deletion corrupts the env.
# Environments are VenvDetector territory.
_ENV_DIRS: frozenset[str] = frozenset({".venv", "site-packages"})
_EXACT_NAMES: frozenset[str] = frozenset({"dist", "build"})
_SUFFIXES: tuple[str, ...] = (".egg-info", ".dist-info")


def _is_artifact_dir(name: str) -> bool:
    if name in _EXACT_NAMES:
        return True
    return any(name.endswith(s) for s in _SUFFIXES)


class ArtifactsDetector(AbstractDetector):
    """Detects Python build artifact directories.

    Finds ``dist/``, ``build/``, ``*.egg-info/``, and ``*.dist-info/``
    directories under the scan root.  Virtual environments (``.venv``,
    any directory containing ``pyvenv.cfg``) and ``site-packages`` trees
    are skipped: their ``*.dist-info`` entries are package metadata, not
    build output.
    """

    name = "artifacts"

    def can_handle(self) -> bool:
        return True  # pure filesystem walk

    def detect(self, path: Path) -> list[Environment]:
        envs: list[Environment] = []
        for current_root, directories, files in os.walk(path, topdown=True):
            if "pyvenv.cfg" in files:
                # Inside a virtual environment (whatever its name) — skip it.
                directories[:] = []
                continue
            pruned = set()
            for d in directories:
                if d in _PRUNED or d in _ENV_DIRS:
                    pruned.add(d)
                    continue
                if _is_artifact_dir(d):
                    artifact_path = Path(current_root) / d
                    try:
                        stat = artifact_path.stat()
                        size = get_total_size(artifact_path)
                        mtime = datetime.fromtimestamp(
                            stat.st_mtime,
                            tz=timezone.utc,
                        )
                        envs.append(
                            Environment(
                                path=artifact_path,
                                name=str(artifact_path),
                                type="artifacts",
                                last_accessed=mtime,
                                size_bytes=size,
                            )
                        )
                    except (FileNotFoundError, OSError) as exc:
                        logger.debug("Skipping %s: %s", artifact_path, exc)
                    pruned.add(d)  # don't recurse inside
            directories[:] = [d for d in directories if d not in pruned]

        return envs
