"""Abstract base class for all killpy detectors."""

from __future__ import annotations

import shutil
from abc import ABC, abstractmethod
from pathlib import Path
from typing import ClassVar

from killpy.models import Environment

# Directory names shared by the filesystem-walking detectors.  Defined once
# here so the prune policy has a single source of truth (see
# ``dev-docs/CODING_CONVENTIONS.md`` §1).

# Version-control and JS dependency directories: never worth descending into
# when looking for Python environments/artifacts.
VCS_PRUNE_DIRS: frozenset[str] = frozenset({".git", ".hg", ".svn", "node_modules"})

# An environment's own internals: a ``.venv`` / ``site-packages`` tree belongs
# to the environment that owns it, so cache/artifact detectors must not descend
# into it and double-count (or wrongly offer to delete) its contents.
ENV_INTERNAL_DIRS: frozenset[str] = frozenset({".venv", "site-packages"})


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

    can_handle() contract
    ---------------------
    :meth:`can_handle` is *not* overridden by concrete detectors.  Instead each
    declares its applicability contract as data, and the base computes the
    result — so the declared contract and the runtime behaviour can never
    diverge.  A detector must declare exactly one of:

    * ``always_available = True`` — pure filesystem walk (venv, tox, cache, artifacts).
    * ``required_tool = "<cli>"`` — needs a CLI on ``PATH`` (conda, pipx).
    * override :meth:`_candidate_dirs` — needs a global directory (poetry, pyenv).
    * both ``required_tool`` and :meth:`_candidate_dirs` — tool *or* directory
      (pipenv, hatch, uv).

    ``tests/unit/test_detectors.py`` asserts every detector declares one.  For a
    check the three knobs can't express, overriding :meth:`can_handle` is an
    allowed, documented exception — see ``dev-docs/ADDING_A_DETECTOR.md``.
    """

    name: str = "base"

    #: CLI executable that, if present on ``PATH``, enables this detector.
    required_tool: ClassVar[str | None] = None
    #: ``True`` for detectors that always apply (pure filesystem walks).
    always_available: ClassVar[bool] = False

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

    def _candidate_dirs(self) -> tuple[Path, ...]:
        """Directories whose existence makes this detector applicable.

        Empty by default; directory- and hybrid-contract detectors override it.
        Resolved at call time (not class-definition time) so patched path
        helpers are honoured.
        """
        return ()

    def can_handle(self) -> bool:
        """Return ``True`` when this detector can find anything on this system.

        Computed from the declared contract (see the class docstring); a
        pre-flight gate that never raises and does no I/O beyond ``which()`` /
        ``exists()``.  Do not override — declare the contract instead.
        """
        if self.always_available:
            return True
        if self.required_tool is not None and shutil.which(self.required_tool):
            return True
        return any(d.exists() for d in self._candidate_dirs())
