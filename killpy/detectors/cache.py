"""Detector for various Python cache directories.

Covers:
* ``__pycache__`` directories (local, from cleaners module)
* ``.mypy_cache``
* ``.pytest_cache``
* ``.ruff_cache``
* Global pip cache  (``~/.cache/pip``)
* Global uv cache   (``~/.cache/uv``)
"""

from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from pathlib import Path

from killpy.detectors.base import AbstractDetector
from killpy.files import get_total_size
from killpy.models import Environment

logger = logging.getLogger(__name__)

# Local cache directories discovered by walking the scan root.
_LOCAL_CACHE_DIRS: tuple[str, ...] = (
    "__pycache__",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
)

# Directories to prune from the walk so we don't descend into them.
_PRUNED: frozenset[str] = frozenset({".git", ".hg", ".svn", "node_modules"})


class CacheDetector(AbstractDetector):
    """Detects local and global Python cache directories."""

    name = "cache"

    def can_handle(self) -> bool:
        return True

    def detect(self, path: Path) -> list[Environment]:
        envs: list[Environment] = []
        envs.extend(self._scan_local(path))
        envs.extend(self._scan_global())
        return envs

    # ------------------------------------------------------------------ #

    def _scan_local(self, root: Path) -> list[Environment]:
        """Walk *root* and collect all known local cache directories."""
        results: list[Environment] = []
        for current_root, directories, _ in os.walk(root, topdown=True):
            prune = set()
            for d in directories:
                if d in _PRUNED:
                    prune.add(d)
                    continue
                if d in _LOCAL_CACHE_DIRS:
                    cache_path = Path(current_root) / d
                    try:
                        env = _make_cache_env(cache_path, d)
                        results.append(env)
                    except (FileNotFoundError, OSError) as exc:
                        logger.debug("Skipping %s: %s", cache_path, exc)
                    prune.add(d)  # don't recurse inside cache dirs
            directories[:] = [d for d in directories if d not in prune]
        return results

    def _scan_global(self) -> list[Environment]:
        """Return global pip and uv cache directories if they exist."""
        results: list[Environment] = []
        candidates = [
            (Path.home() / ".cache" / "pip", "pip-cache"),
            (Path.home() / ".cache" / "uv", "uv-cache"),
        ]
        for cache_path, tag in candidates:
            if cache_path.exists():
                try:
                    results.append(_make_cache_env(cache_path, tag))
                except (FileNotFoundError, OSError) as exc:
                    logger.debug("Skipping global cache %s: %s", cache_path, exc)
        return results


def _make_cache_env(p: Path, tag: str) -> Environment:
    stat = p.stat()
    size = get_total_size(p)
    mtime = datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc)
    return Environment(
        path=p,
        name=str(p),
        type=tag,
        last_accessed=mtime,
        size_bytes=size,
    )
