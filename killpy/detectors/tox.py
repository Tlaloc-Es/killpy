"""Detector for tox environment directories (``.tox/``)."""

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


class ToxDetector(AbstractDetector):
    """Detects ``.tox`` directories created by tox test automation."""

    name = "tox"

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
                if d == ".tox":
                    tox_path = Path(current_root) / d
                    try:
                        stat = tox_path.stat()
                        size = get_total_size(tox_path)
                        mtime = datetime.fromtimestamp(
                            stat.st_mtime,
                            tz=timezone.utc,
                        )
                        envs.append(
                            Environment(
                                path=tox_path,
                                name=str(tox_path),
                                type="tox",
                                last_accessed=mtime,
                                size_bytes=size,
                            )
                        )
                    except (FileNotFoundError, OSError) as exc:
                        logger.debug("Skipping %s: %s", tox_path, exc)
                    pruned.add(d)
            directories[:] = [d for d in directories if d not in pruned]

        return envs
