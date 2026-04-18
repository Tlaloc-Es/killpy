"""Detector for pipx-managed packages."""

from __future__ import annotations

import json
import logging
import platform
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from killpy.detectors.base import AbstractDetector
from killpy.files import get_total_size
from killpy.models import Environment

logger = logging.getLogger(__name__)


def _pipx_venvs_root() -> Path:
    """Return the root directory where pipx stores its package venvs."""
    if platform.system() == "Windows":  # pragma: no cover
        local_app = (
            Path.home() / "AppData" / "Local" / "pipx" / "venvs"
        )  # pragma: no cover
        if local_app.exists():  # pragma: no cover
            return local_app  # pragma: no cover
    # XDG_DATA_HOME / pipx / venvs (Linux/macOS default)
    xdg = Path.home() / ".local" / "share" / "pipx" / "venvs"
    return xdg


def _resolve_pipx_candidate(
    package_name: str, pkg_data: dict, venvs_root: Path
) -> Path | None:
    """Return the venv directory for a pipx package, or ``None`` if not found."""
    candidate = venvs_root / package_name
    if candidate.exists():
        return candidate

    app_paths = (
        pkg_data.get("metadata", {}).get("main_package", {}).get("app_paths", [])
    )
    if not app_paths:
        return None
    raw = app_paths[0].get("__Path__", "")
    if not raw:
        return None
    # bin/<exe>  →  venvs/<pkg>
    candidate = Path(raw).parent.parent / package_name
    if not candidate.exists():
        candidate = Path(raw).parent
    if not candidate.exists():
        logger.debug("Cannot locate venv dir for pipx package %s", package_name)
        return None
    return candidate


class PipxDetector(AbstractDetector):
    """Detects pipx packages via ``pipx list --json``.

    Size is computed from the actual venv directory under the pipx venvs
    root, not from the bin-symlink directory (which would report near-zero).
    """

    name = "pipx"

    def can_handle(self) -> bool:
        return shutil.which("pipx") is not None

    def detect(self, path: Path) -> list[Environment]:  # noqa: ARG002
        try:
            result = subprocess.run(
                ["pipx", "list", "--json"],
                capture_output=True,
                text=True,
                check=True,
            )
        except FileNotFoundError:
            return []
        except subprocess.CalledProcessError as exc:
            logger.debug("pipx list --json failed: %s", exc)
            return []
        except OSError as exc:
            logger.debug("OS error running pipx: %s", exc)
            return []

        try:
            data = json.loads(result.stdout)
        except json.JSONDecodeError as exc:
            logger.error("Invalid JSON from pipx: %s", exc)
            return []

        venvs_root = _pipx_venvs_root()
        envs: list[Environment] = []

        for package_name, pkg_data in data.get("venvs", {}).items():
            candidate = _resolve_pipx_candidate(package_name, pkg_data, venvs_root)
            if candidate is None:
                continue

            try:
                stat = candidate.stat()
                size = get_total_size(candidate)
                mtime = datetime.fromtimestamp(
                    stat.st_mtime,
                    tz=timezone.utc,
                )
                envs.append(
                    Environment(
                        path=candidate,
                        name=package_name,
                        type="pipx",
                        last_accessed=mtime,
                        size_bytes=size,
                        managed_by="pipx",
                    )
                )
            except (FileNotFoundError, OSError) as exc:
                logger.debug("Skipping pipx package %s: %s", package_name, exc)

        return envs
