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
from collections.abc import AsyncIterator, Callable
from pathlib import Path

from killpy.detectors import ALL_DETECTORS, AbstractDetector
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
    ) -> None:
        if detectors is not None:
            self._detectors = detectors
        else:
            self._detectors = [cls() for cls in ALL_DETECTORS]

        if types is not None:
            self._detectors = [d for d in self._detectors if d.name in types]

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

        for detector in self._detectors:
            if not detector.can_handle():
                logger.debug("Skipping %s (can_handle=False)", detector.name)
                continue
            try:
                found = detector.detect(path)
            except Exception as exc:  # noqa: BLE001
                logger.warning("Detector %s raised: %s", detector.name, exc)
                found = []

            deduped = self._deduplicate(found, seen)
            results.extend(deduped)

            if on_progress is not None:
                on_progress(detector, deduped)

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
        seen: set[Path] = set()

        async def _run(detector: AbstractDetector):
            try:
                return detector, await asyncio.to_thread(detector.detect, path)
            except Exception as exc:  # noqa: BLE001
                logger.warning("Detector %s raised: %s", detector.name, exc)
                return detector, []

        tasks = [asyncio.create_task(_run(d)) for d in applicable]
        for coro in asyncio.as_completed(tasks):
            detector, found = await coro
            deduped = self._deduplicate(found, seen)
            yield detector, deduped

    # ------------------------------------------------------------------ #
    #  Helpers                                                             #
    # ------------------------------------------------------------------ #

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
