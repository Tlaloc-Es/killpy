"""Detector for uv-managed virtual environments."""

from __future__ import annotations

import logging
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path

from killpy.detectors.base import AbstractDetector
from killpy.files import get_total_size
from killpy.models import Environment

logger = logging.getLogger(__name__)

_PRUNED: frozenset[str] = frozenset({".git", ".hg", ".svn", "node_modules"})


class UvDetector(AbstractDetector):
    """Detects ``.uv`` directories created by `uv venv` inside projects.

    Also reports the global uv cache at ``~/.cache/uv`` – but only when
    the cache detector is *not* included in the same scan (the scanner
    handles deduplication by path).
    """

    name = "uv"

    def can_handle(self) -> bool:
        return shutil.which("uv") is not None

    def detect(self, path: Path) -> list[Environment]:
        envs: list[Environment] = []
        for current_root, directories, _ in os.walk(path, topdown=True):
            pruned = set()
            for d in directories:
                if d in _PRUNED:
                    pruned.add(d)
                    continue
                if d == ".uv":
                    uv_path = Path(current_root) / d
                    try:
                        stat = uv_path.stat()
                        size = get_total_size(uv_path)
                        mtime = datetime.fromtimestamp(
                            stat.st_mtime, tz=timezone.utc,
                        )
                        envs.append(
                            Environment(
                                path=uv_path,
                                name=str(uv_path),
                                type="uv",
                                last_accessed=mtime,
                                size_bytes=size,
                            )
                        )
                    except (FileNotFoundError, OSError) as exc:
                        logger.debug("Skipping %s: %s", uv_path, exc)
                    pruned.add(d)
            directories[:] = [d for d in directories if d not in pruned]

        envs.sort(key=lambda e: e.size_bytes, reverse=True)
        return envs
