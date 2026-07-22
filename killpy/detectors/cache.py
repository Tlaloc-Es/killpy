"""Detector for various Python cache directories.

Covers:
* ``__pycache__`` directories (local, from cleaners module)
* ``.mypy_cache``
* ``.pytest_cache``
* ``.ruff_cache``
* Global pip cache  (``~/.cache/pip``) — only when inside the scanned path
* Global uv cache   (``~/.cache/uv``) — only when inside the scanned path
"""

from __future__ import annotations

import logging
import os
import platform
from datetime import datetime, timezone
from pathlib import Path

from killpy.detectors.base import (
    ENV_INTERNAL_DIRS,
    VCS_PRUNE_DIRS,
    AbstractDetector,
)
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

# Caches inside an environment (``ENV_INTERNAL_DIRS``) belong to the
# environment: VenvDetector already reports the whole tree, so listing them
# separately would double-count their size in stats/list totals.


def _pip_cache_dir() -> Path:
    """Return pip's cache directory, honouring env vars and the platform."""
    override = os.environ.get("PIP_CACHE_DIR")
    if override:
        return Path(override).expanduser()
    system = platform.system()
    if system == "Windows":  # pragma: no cover
        return Path.home() / "AppData" / "Local" / "pip" / "cache"  # pragma: no cover
    if system == "Darwin":
        return Path.home() / "Library" / "Caches" / "pip"
    xdg = os.environ.get("XDG_CACHE_HOME")
    base = Path(xdg) if xdg else Path.home() / ".cache"
    return base / "pip"


def _uv_cache_dir() -> Path:
    """Return uv's cache directory (uv uses XDG-style paths on all Unixes)."""
    override = os.environ.get("UV_CACHE_DIR")
    if override:
        return Path(override).expanduser()
    if platform.system() == "Windows":  # pragma: no cover
        return Path.home() / "AppData" / "Local" / "uv" / "cache"  # pragma: no cover
    xdg = os.environ.get("XDG_CACHE_HOME")
    base = Path(xdg) if xdg else Path.home() / ".cache"
    return base / "uv"


class CacheDetector(AbstractDetector):
    """Detects local and global Python cache directories."""

    name = "cache"
    always_available = True  # pure filesystem walk
    shared_walk = True  # local tree scan served by killpy.detectors._shared_walk

    def detect(self, path: Path) -> list[Environment]:
        envs: list[Environment] = []
        envs.extend(self._scan_local(path))
        envs.extend(self._scan_global(path))
        return envs

    def scan_global(self, path: Path) -> list[Environment]:
        """Global pip/uv caches — the part not covered by the shared tree walk."""
        return self._scan_global(path)

    # ------------------------------------------------------------------ #

    def _scan_local(self, root: Path) -> list[Environment]:
        """Walk *root* and collect all known local cache directories.

        Virtual environments (``.venv``, any directory containing
        ``pyvenv.cfg``) and ``site-packages`` trees are skipped.
        """
        results: list[Environment] = []
        for current_root, directories, files in os.walk(root, topdown=True):
            if "pyvenv.cfg" in files:
                # Inside a virtual environment (whatever its name) — skip it.
                directories[:] = []
                continue
            pruned = set()
            for d in directories:
                if d in VCS_PRUNE_DIRS or d in ENV_INTERNAL_DIRS:
                    pruned.add(d)
                    continue
                if d in _LOCAL_CACHE_DIRS:
                    cache_path = Path(current_root) / d
                    try:
                        env = _make_cache_env(cache_path, d)
                        results.append(env)
                    except (FileNotFoundError, OSError) as exc:
                        logger.debug("Skipping %s: %s", cache_path, exc)
                    pruned.add(d)  # don't recurse inside cache dirs
            directories[:] = [d for d in directories if d not in pruned]
        return results

    def _scan_global(self, root: Path) -> list[Environment]:
        """Return global pip/uv cache directories that live under *root*.

        A scan scoped to a project directory (e.g. the pre-commit hooks or
        ``killpy delete --type cache --path <repo>``) must never surface —
        and therefore never delete — caches outside that directory.  The
        global caches are still reported when the scan root contains them
        (e.g. ``killpy --path ~``).
        """
        try:
            scan_root = root.resolve()
        except OSError:
            scan_root = root
        results: list[Environment] = []
        candidates = [
            (_pip_cache_dir(), "pip-cache"),
            (_uv_cache_dir(), "uv-cache"),
        ]
        for cache_path, tag in candidates:
            if not cache_path.exists():
                continue
            try:
                if not cache_path.resolve().is_relative_to(scan_root):
                    continue
                results.append(_make_cache_env(cache_path, tag))
            except (FileNotFoundError, OSError) as exc:
                logger.debug("Skipping global cache %s: %s", cache_path, exc)
        return results


def _make_cache_env(cache_path: Path, tag: str) -> Environment:
    stat = cache_path.stat()
    size = get_total_size(cache_path)
    mtime = datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc)
    return Environment(
        path=cache_path,
        name=str(cache_path),
        type=tag,
        last_modified=mtime,
        size_bytes=size,
    )
