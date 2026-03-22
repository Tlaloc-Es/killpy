"""Cleaner – handles deletion of detected environments.

Usage::

    from killpy.cleaner import Cleaner
    from killpy.models import Environment

    cleaner = Cleaner()
    freed = cleaner.delete(env, dry_run=False)

The :class:`Cleaner` dispatches to the correct removal strategy based on
:attr:`~killpy.models.Environment.managed_by`.  Environments with
``managed_by="conda"`` are removed via ``conda env remove``;
``managed_by="pipx"`` via ``pipx uninstall``; all others via
:func:`shutil.rmtree`.
"""

from __future__ import annotations

import logging
import shutil
import subprocess
from collections.abc import Callable
from pathlib import Path

from killpy.models import Environment

logger = logging.getLogger(__name__)


class CleanerError(Exception):
    """Raised when a deletion operation fails."""


class Cleaner:
    """Deletes :class:`~killpy.models.Environment` instances.

    Parameters
    ----------
    dry_run:
        When ``True`` no destructive operations are performed; the method
        still returns the would-be size so callers can show totals.
    """

    def __init__(self, dry_run: bool = False) -> None:
        self.dry_run = dry_run

    # ------------------------------------------------------------------ #
    #  Public API                                                          #
    # ------------------------------------------------------------------ #

    def delete(self, env: Environment) -> int:
        """Delete a single environment.

        Parameters
        ----------
        env:
            The environment to remove.

        Returns
        -------
        int
            Number of bytes freed (or that *would have been* freed in dry-run
            mode).

        Raises
        ------
        CleanerError
            If the underlying removal command fails.
        """
        if self.dry_run:
            logger.info("[dry-run] Would delete %s (%s)", env.path, env.size_human)
            return env.size_bytes

        try:
            if env.managed_by == "conda":
                self._remove_conda(env.name)
            elif env.managed_by == "pipx":
                self._remove_pipx(env.name)
            else:
                self._remove_filesystem(env.path)
        except CleanerError:
            raise
        except Exception as exc:  # noqa: BLE001
            raise CleanerError(f"Failed to delete {env.path}: {exc}") from exc

        logger.info("Deleted %s (%s)", env.path, env.size_human)
        return env.size_bytes

    def delete_many(
        self,
        envs: list[Environment],
        on_progress: Callable[[Environment, int, int], None] | None = None,
    ) -> int:
        """Delete a list of environments, accumulating freed bytes.

        Parameters
        ----------
        envs:
            Environments to delete.
        on_progress:
            Optional callback invoked after each deletion.  Receives
            *(env, freed_this_item, total_freed_so_far)*.

        Returns
        -------
        int
            Total bytes freed.
        """
        total = 0
        for env in envs:
            try:
                freed = self.delete(env)
                total += freed
            except CleanerError as exc:
                logger.error("%s", exc)
                freed = 0

            if on_progress is not None:
                on_progress(env, freed, total)

        return total

    # ------------------------------------------------------------------ #
    #  Removal strategies                                                  #
    # ------------------------------------------------------------------ #

    @staticmethod
    def _remove_filesystem(path: Path) -> None:
        if not path.exists():
            logger.warning("Path no longer exists: %s", path)
            return
        shutil.rmtree(path)

    @staticmethod
    def _remove_conda(env_name: str) -> None:
        if shutil.which("conda") is None:
            raise CleanerError("conda not found on PATH")
        result = subprocess.run(
            ["conda", "env", "remove", "--name", env_name, "--yes"],
            check=False,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            raise CleanerError(
                f"conda env remove failed for '{env_name}': {result.stderr.strip()}"
            )

    @staticmethod
    def _remove_pipx(package_name: str) -> None:
        if shutil.which("pipx") is None:
            raise CleanerError("pipx not found on PATH")
        result = subprocess.run(
            ["pipx", "uninstall", package_name],
            check=False,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            raise CleanerError(
                f"pipx uninstall failed for '{package_name}': {result.stderr.strip()}"
            )
