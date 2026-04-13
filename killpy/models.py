"""
Core data models for killpy.

All detectors produce :class:`Environment` instances; the TUI and CLI
commands consume them.  Using a proper dataclass instead of raw tuples
makes the contract between layers explicit and IDE-friendly.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from killpy.files import format_size


@dataclass
class Environment:
    """A single detected Python environment or cache directory.

    Attributes
    ----------
    path:
        Filesystem path of the environment root.  For subprocess-managed
        environments (conda, pipx) this is the physical venv directory used
        for size calculation and display.
    name:
        Human-readable name.  For filesystem envs this defaults to the last
        two parts of *path*; for named envs (conda, pipx) it is the package /
        environment name.
    type:
        Short detector tag, e.g. ``"venv"``, ``"pyvenv.cfg"``, ``"poetry"``,
        ``"conda"``, ``"pipx"``, ``"cache"``, ``"uv"``, ``"artifacts"``…
    last_accessed:
        Timestamp of the last modification reported by the filesystem.
    size_bytes:
        Total size in bytes (recursive directory sum).
    managed_by:
        If not ``None``, the external tool that manages deletion.  Supported
        values: ``"conda"`` and ``"pipx"``.  When ``None`` deletion is
        performed via :func:`shutil.rmtree`.
    """

    path: Path
    name: str
    type: str
    last_accessed: datetime
    size_bytes: int
    managed_by: str | None = None
    is_system_critical: bool = False

    # ------------------------------------------------------------------ #
    #  Computed helpers                                                    #
    # ------------------------------------------------------------------ #

    @property
    def size_human(self) -> str:
        """Human-readable size string (GB / MB / KB / bytes)."""
        return format_size(self.size_bytes)

    @property
    def last_accessed_str(self) -> str:
        """Formatted date string ``DD/MM/YYYY`` for display."""
        return self.last_accessed.strftime("%d/%m/%Y")

    # ------------------------------------------------------------------ #
    #  Serialisation                                                       #
    # ------------------------------------------------------------------ #

    def to_dict(self) -> dict:
        """Return a JSON-serialisable representation."""
        abs_path = self.path.resolve()
        try:
            rel_path = abs_path.relative_to(Path.cwd())
        except ValueError:
            rel_path = abs_path
        return {
            "path": str(rel_path),
            "absolute_path": str(abs_path),
            "name": self.name,
            "type": self.type,
            "last_accessed": self.last_accessed.isoformat(),
            "size_bytes": self.size_bytes,
            "size_human": self.size_human,
            "managed_by": self.managed_by,
            "is_system_critical": self.is_system_critical,
        }
