"""Detector for Python build artifacts (dist/, build/, *.egg-info/, *.dist-info/)."""

from __future__ import annotations

import logging
import os
from datetime import datetime
from pathlib import Path

from killpy.detectors.base import AbstractDetector
from killpy.files import get_total_size
from killpy.models import Environment

logger = logging.getLogger(__name__)

_PRUNED: frozenset[str] = frozenset({".git", ".hg", ".svn", "node_modules"})
_EXACT_NAMES: frozenset[str] = frozenset({"dist", "build"})
_SUFFIXES: tuple[str, ...] = (".egg-info", ".dist-info")


def _is_artifact_dir(name: str) -> bool:
    if name in _EXACT_NAMES:
        return True
    return any(name.endswith(s) for s in _SUFFIXES)


class ArtifactsDetector(AbstractDetector):
    """Detects Python build artifact directories.

    Finds ``dist/``, ``build/``, ``*.egg-info/``, and ``*.dist-info/``
    directories under the scan root.
    """

    name = "artifacts"

    def can_handle(self) -> bool:
        return True  # pure filesystem walk

    def detect(self, path: Path) -> list[Environment]:
        envs: list[Environment] = []
        for current_root, directories, _ in os.walk(path, topdown=True):
            pruned = set()
            for d in directories:
                if d in _PRUNED:
                    pruned.add(d)
                    continue
                if _is_artifact_dir(d):
                    artifact_path = Path(current_root) / d
                    try:
                        stat = artifact_path.stat()
                        size = get_total_size(artifact_path)
                        envs.append(
                            Environment(
                                path=artifact_path,
                                name=str(artifact_path),
                                type="artifacts",
                                last_accessed=datetime.fromtimestamp(stat.st_mtime),
                                size_bytes=size,
                            )
                        )
                    except (FileNotFoundError, OSError) as exc:
                        logger.debug("Skipping %s: %s", artifact_path, exc)
                    pruned.add(d)  # don't recurse inside
            directories[:] = [d for d in directories if d not in pruned]

        envs.sort(key=lambda e: e.size_bytes, reverse=True)
        return envs
