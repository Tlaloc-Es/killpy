"""Detector for Conda environments."""

from __future__ import annotations

import logging
import shutil
import subprocess
from datetime import datetime
from pathlib import Path

from killpy.detectors.base import AbstractDetector
from killpy.files import get_total_size
from killpy.models import Environment

logger = logging.getLogger(__name__)

_MIN_FIELDS = 2


class CondaDetector(AbstractDetector):
    """Detects Conda environments via ``conda env list``.

    The scan *path* argument is ignored – conda manages its own registry.
    """

    name = "conda"

    def can_handle(self) -> bool:
        return shutil.which("conda") is not None

    def detect(self, path: Path) -> list[Environment]:  # noqa: ARG002
        try:
            result = subprocess.run(
                ["conda", "env", "list"],
                capture_output=True,
                text=True,
                check=True,
            )
        except FileNotFoundError:
            return []
        except subprocess.CalledProcessError as exc:
            logger.debug("conda env list failed: %s", exc)
            return []
        except OSError as exc:
            logger.debug("OS error running conda: %s", exc)
            return []

        envs: list[Environment] = []
        for line in result.stdout.splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue

            fields = line.split()
            # Skip the currently-active environment (marked with *)
            if "*" in fields:
                continue
            if len(fields) < _MIN_FIELDS:
                logger.debug("Skipping malformed conda row: %r", line)
                continue

            env_name = fields[0]
            env_path = Path(fields[-1])
            try:
                stat = env_path.stat()
                size = get_total_size(env_path)
                envs.append(
                    Environment(
                        path=env_path,
                        name=env_name,
                        type="conda",
                        last_accessed=datetime.fromtimestamp(stat.st_mtime),
                        size_bytes=size,
                        managed_by="conda",
                    )
                )
            except (FileNotFoundError, OSError) as exc:
                logger.debug("Skipping inaccessible conda env %s: %s", env_path, exc)

        envs.sort(key=lambda e: e.size_bytes, reverse=True)
        return envs
