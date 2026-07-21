"""Detector for Conda environments."""

from __future__ import annotations

import logging
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from killpy.detectors.base import AbstractDetector
from killpy.files import get_total_size
from killpy.models import Environment

logger = logging.getLogger(__name__)


def _looks_like_path(text: str) -> bool:
    """Return True when *text* starts with a filesystem path (not an env name)."""
    if text.startswith(("/", "\\")):
        return True
    return len(text) > 1 and text[1] == ":"  # Windows drive, e.g. C:\...


def _parse_env_line(line: str) -> tuple[str, Path, bool] | None:
    """Parse one ``conda env list`` row into ``(name, path, is_active)``.

    Rows look like ``name  [*]  /path`` or, for environments created with
    ``--prefix``, just ``[*]  /path``.  The path may contain spaces, so it
    must be taken as the whole remainder of the line — not the last
    whitespace-separated token.
    """
    rest = line.strip()
    name = ""
    if not rest.startswith("*") and not _looks_like_path(rest):
        name, _, rest = rest.partition(" ")
        rest = rest.strip()
        if not rest:
            return None
    is_active = rest.startswith("*")
    if is_active:
        rest = rest[1:].strip()
    if not rest:
        return None
    path = Path(rest)
    return name or path.name, path, is_active


class CondaDetector(AbstractDetector):
    """Detects Conda environments via ``conda env list``.

    The scan *path* argument is ignored – conda manages its own registry.
    """

    name = "conda"
    required_tool = "conda"  # needs the conda CLI on PATH

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
        for raw_line in result.stdout.splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue

            parsed = _parse_env_line(line)
            if parsed is None:
                logger.debug("Skipping malformed conda row: %r", line)
                continue
            env_name, env_path, is_active = parsed
            # Never offer the currently-active environment for deletion.
            if is_active:
                continue
            try:
                stat = env_path.stat()
                size = get_total_size(env_path)
                mtime = datetime.fromtimestamp(
                    stat.st_mtime,
                    tz=timezone.utc,
                )
                envs.append(
                    Environment(
                        path=env_path,
                        name=env_name,
                        type="conda",
                        last_modified=mtime,
                        size_bytes=size,
                        managed_by="conda",
                    )
                )
            except (FileNotFoundError, OSError) as exc:
                logger.debug("Skipping inaccessible conda env %s: %s", env_path, exc)

        return envs
