"""Abstract base class for all killpy detectors."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

from killpy.models import Environment


class AbstractDetector(ABC):
    """Common interface every detector must implement.

    Concrete detectors live in this package (``killpy/detectors/``).  The
    :class:`~killpy.scanner.Scanner` instantiates them and calls
    :meth:`can_handle` before :meth:`detect`, so detectors that rely on
    optional tools (conda, pipx …) are silently skipped when those tools
    are not present.

    Class attributes
    ----------------
    name : str
        Short identifier used for logging, filtering and the ``--type``
        CLI option.  Must be unique across all detectors.
    """

    name: str = "base"

    @abstractmethod
    def detect(self, path: Path) -> list[Environment]:
        """Scan *path* and return every matching :class:`~killpy.models.Environment`.

        Implementations **must not raise** – on error they should log and
        return an empty list so that other detectors are unaffected.

        Parameters
        ----------
        path:
            Root directory to scan.  Global-cache detectors (poetry, pipx …)
            may ignore this argument; local detectors (venv, tox …) should
            use it as the walk root.
        """

    @abstractmethod
    def can_handle(self) -> bool:
        """Return ``True`` when this detector is usable in the current environment.

        Examples of conditions to check:

        * Required CLI tool is on ``PATH`` (conda, pipx …).
        * Required cache directory exists (poetry, pipenv …).
        * Always ``True`` for pure filesystem detectors (venv, cache …).
        """
