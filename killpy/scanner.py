"""Scanner – orchestrates all detectors and returns a deduplicated result list.

Usage::

    from killpy.scanner import Scanner

    scanner = Scanner()
    envs = scanner.scan(Path("/home/user/projects"))

The :meth:`Scanner.scan` variant is synchronous and suitable for CLI commands.
:meth:`Scanner.scan_async` is an async generator that yields
:class:`~killpy.models.Environment` objects progressively as each detector
finishes, which is used by the TUI for live updates.
"""

from __future__ import annotations

import asyncio
import logging
import sys
from collections.abc import AsyncIterator, Callable
from pathlib import Path

from killpy.detectors import ALL_DETECTORS, AbstractDetector
from killpy.detectors._shared_walk import TYPE_TO_DETECTOR, walk_environments
from killpy.detectors.pyenv import _pyenv_root
from killpy.models import Environment

logger = logging.getLogger(__name__)


class Scanner:
    """Orchestrates all (or a subset of) detectors and deduplicates results.

    Parameters
    ----------
    detectors:
        Explicit list of *instances* to use.  When ``None`` every class from
        :data:`~killpy.detectors.ALL_DETECTORS` is instantiated.
    types:
        Optional set of detector :attr:`~killpy.detectors.base.AbstractDetector.name`
        strings to limit scanning to.  When ``None`` all detectors are used.
    """

    def __init__(
        self,
        detectors: list[AbstractDetector] | None = None,
        types: set[str] | None = None,
        excluded: set[str] | None = None,
    ) -> None:
        if detectors is not None:
            self._detectors = detectors
        else:
            self._detectors = [cls() for cls in ALL_DETECTORS]

        if types is not None:
            self._detectors = [d for d in self._detectors if d.name in types]

        self._excluded: set[str] = excluded or set()

    # ------------------------------------------------------------------ #
    #  Public API                                                          #
    # ------------------------------------------------------------------ #

    def scan(
        self,
        path: Path,
        on_progress: Callable[[AbstractDetector, list[Environment]], None]
        | None = None,
    ) -> list[Environment]:
        """Scan *path* synchronously with all applicable detectors.

        Parameters
        ----------
        path:
            Root directory to pass to each detector.
        on_progress:
            Optional callback invoked after each detector finishes.  Receives
            the detector instance and the list of environments found by it.

        Returns
        -------
        list[Environment]
            Deduplicated, size-sorted list of all detected environments.
        """
        seen: set[Path] = set()
        results: list[Environment] = []

        applicable = [d for d in self._detectors if d.can_handle()]
        shared = [d for d in applicable if d.shared_walk]
        others = [d for d in applicable if not d.shared_walk]

        # One traversal shared by every filesystem-walking detector.
        for detector, found in self._shared_walk_groups(shared, path):
            processed = self._process(found, seen)
            results.extend(processed)
            if on_progress is not None:
                on_progress(detector, processed)

        # The remaining detectors scan their own global directories.
        for detector in others:
            try:
                found = detector.detect(path)
            except Exception as exc:  # noqa: BLE001
                logger.warning("Detector %s raised: %s", detector.name, exc)
                found = []
            processed = self._process(found, seen)
            results.extend(processed)
            if on_progress is not None:
                on_progress(detector, processed)

        results.sort(key=lambda e: e.size_bytes, reverse=True)
        return results

    async def scan_async(
        self, path: Path
    ) -> AsyncIterator[tuple[AbstractDetector, list[Environment]]]:
        """Async generator that yields *(detector, envs)* tuples progressively.

        Each applicable detector is run in a thread via
        :func:`asyncio.to_thread` so the event loop is never blocked.  Results
        are yielded as soon as each detector finishes (first-come-first-served).

        Usage::

            async for detector, envs in scanner.scan_async(path):
                for env in envs:
                    table.add_row(env)
        """
        applicable = [d for d in self._detectors if d.can_handle()]
        shared = [d for d in applicable if d.shared_walk]
        others = [d for d in applicable if not d.shared_walk]
        seen: set[Path] = set()

        async def _run_shared() -> list[tuple[AbstractDetector, list[Environment]]]:
            try:
                return await asyncio.to_thread(self._shared_walk_groups, shared, path)
            except Exception as exc:  # noqa: BLE001
                logger.warning("Shared walk raised: %s", exc)
                return [(d, []) for d in shared]

        async def _run_one(
            detector: AbstractDetector,
        ) -> list[tuple[AbstractDetector, list[Environment]]]:
            try:
                return [(detector, await asyncio.to_thread(detector.detect, path))]
            except Exception as exc:  # noqa: BLE001
                logger.warning("Detector %s raised: %s", detector.name, exc)
                return [(detector, [])]

        tasks = [asyncio.create_task(_run_one(d)) for d in others]
        if shared:
            tasks.append(asyncio.create_task(_run_shared()))

        for coro in asyncio.as_completed(tasks):
            for detector, found in await coro:
                deduped = self._process(found, seen)
                yield detector, deduped

    # ------------------------------------------------------------------ #
    #  Helpers                                                             #
    # ------------------------------------------------------------------ #

    def _shared_walk_groups(
        self, shared: list[AbstractDetector], path: Path
    ) -> list[tuple[AbstractDetector, list[Environment]]]:
        """Run the one shared walk, returning ``(detector, envs)`` per detector.

        The local tree is walked once for the union of *shared* detector names;
        each detector also contributes its own global scan (pip/uv caches).
        Results are grouped back per detector via :data:`TYPE_TO_DETECTOR` so the
        per-detector progress contract is preserved.
        """
        if not shared:
            return []
        active = {d.name for d in shared}
        found = walk_environments(path, active)
        for detector in shared:
            found.extend(detector.scan_global(path))
        by_name: dict[str, list[Environment]] = {d.name: [] for d in shared}
        for env in found:
            name = TYPE_TO_DETECTOR.get(env.type)
            if name in by_name:
                by_name[name].append(env)
        return [(d, by_name[d.name]) for d in shared]

    def _process(self, found: list[Environment], seen: set[Path]) -> list[Environment]:
        """Deduplicate, apply exclusions, and flag system-critical envs."""
        deduped = self._deduplicate(found, seen)
        deduped = self._apply_exclusions(deduped)
        for env in deduped:
            self._mark_system_critical(env)
        return deduped

    @staticmethod
    def _deduplicate(envs: list[Environment], seen: set[Path]) -> list[Environment]:
        """Filter out environments whose resolved path has already been seen.

        *seen* is mutated in-place so that callers accumulating results across
        multiple detector runs share the same deduplication set.
        """
        result: list[Environment] = []
        for env in envs:
            try:
                resolved = env.path.resolve()
            except OSError:
                resolved = env.path
            if resolved not in seen:
                seen.add(resolved)
                result.append(env)
        return result

    def _apply_exclusions(self, envs: list[Environment]) -> list[Environment]:
        """Remove environments whose path contains any of the excluded patterns."""
        if not self._excluded:
            return envs
        return [
            e
            for e in envs
            if not any(pattern in str(e.path) for pattern in self._excluded)
        ]

    @staticmethod
    def _mark_system_critical(env: Environment) -> None:
        """Flag an environment as system-critical when it is the currently active env.

        Uses ``sys.prefix`` (the root of the running venv/interpreter) so that only
        the exact environment killpy itself is running inside is flagged — not every
        venv that happens to share the same base Python binary.
        """
        try:
            active_prefix = Path(sys.prefix).resolve()
            if env.path.resolve() == active_prefix:
                env.is_system_critical = True
                return
        except OSError:
            pass

        if env.type == "pyenv":
            global_version_file = _pyenv_root() / "version"
            try:
                global_version = global_version_file.read_text().strip()
                # Compare the exact directory name: endswith() would also
                # match e.g. "my-3.12.1" when the global version is "3.12.1".
                if global_version and global_version in (env.name, env.path.name):
                    env.is_system_critical = True
            except OSError:
                pass
