"""Single shared filesystem walk for the tree-walking detectors.

``venv`` / ``cache`` / ``artifacts`` / ``tox`` each used to run their own
``os.walk`` over the scan root, and ``get_total_size`` re-walked every
environment they found — walking a large tree several times over.

This module performs **one** traversal: each directory is classified as an
environment *container* (a venv, a cache dir, a build artifact, or ``.tox``);
a match is recorded, its size is summed once, and its subtree is pruned.
Environment pruning is always applied — once a venv is found, nothing inside it
is scanned again — which also collapses the cache/artifact double-counting that
used to happen inside environments.

Callers pass the set of detector names whose results they want (``active``).
Pruning happens on every container regardless of ``active``, so asking for a
subset yields exactly what running those detectors alone would.
"""

from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from pathlib import Path

from killpy.detectors.base import VCS_PRUNE_DIRS
from killpy.files import get_total_size
from killpy.models import Environment

logger = logging.getLogger(__name__)

_CACHE_DIRS = frozenset({"__pycache__", ".mypy_cache", ".pytest_cache", ".ruff_cache"})
_ARTIFACT_EXACT = frozenset({"dist", "build"})
_ARTIFACT_SUFFIXES = (".egg-info", ".dist-info")

#: Map every ``Environment.type`` the shared walk (and the cache global scan)
#: can produce back to the detector that owns it — used to group results per
#: detector for progress callbacks.
TYPE_TO_DETECTOR: dict[str, str] = {
    ".venv": "venv",
    "pyvenv.cfg": "venv",
    "__pycache__": "cache",
    ".mypy_cache": "cache",
    ".pytest_cache": "cache",
    ".ruff_cache": "cache",
    "pip-cache": "cache",
    "uv-cache": "cache",
    "artifacts": "artifacts",
    "tox": "tox",
}


def _classify(basename: str, filenames: list[str]) -> tuple[str, str] | None:
    """Return ``(detector_name, env_type)`` if the dir is a container, else ``None``."""
    if basename == ".venv" or "pyvenv.cfg" in filenames:
        return ("venv", ".venv" if basename == ".venv" else "pyvenv.cfg")
    if basename in _CACHE_DIRS:
        return ("cache", basename)
    if basename in _ARTIFACT_EXACT or any(
        basename.endswith(suffix) for suffix in _ARTIFACT_SUFFIXES
    ):
        return ("artifacts", "artifacts")
    if basename == ".tox":
        return ("tox", "tox")
    return None


def _make_env(path: Path, env_type: str) -> Environment | None:
    """Build an :class:`Environment` for *path*, summing its size once."""
    try:
        stat = path.stat()
        return Environment(
            path=path,
            name=str(path),
            type=env_type,
            last_modified=datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc),
            size_bytes=get_total_size(path),
        )
    except (FileNotFoundError, OSError) as exc:
        logger.debug("Skipping %s: %s", path, exc)
        return None


def walk_environments(root: Path, active: set[str]) -> list[Environment]:
    """Walk *root* once and return environments for the ``active`` detector set.

    Each directory that matches a container type is reported (when its detector
    is in *active*) and its subtree pruned; VCS and ``site-packages`` trees are
    never descended into.
    """
    envs: list[Environment] = []
    for current, dirnames, filenames in os.walk(root, topdown=True):
        dirnames[:] = [d for d in dirnames if d not in VCS_PRUNE_DIRS]
        current_path = Path(current)
        if current_path != root:
            match = _classify(current_path.name, filenames)
            if match is not None:
                detector_name, env_type = match
                if detector_name in active:
                    env = _make_env(current_path, env_type)
                    if env is not None:
                        envs.append(env)
                dirnames[:] = []  # env-pruning: never descend into a container
                continue
        # A bare ``site-packages`` (e.g. a conda env, which has no pyvenv.cfg) is
        # not a container but must not be scanned for caches/artifacts. ``.venv``
        # IS a container — detected on entry — so it is deliberately not pruned
        # here (that would stop us from ever reporting it).
        dirnames[:] = [d for d in dirnames if d != "site-packages"]
    return envs
