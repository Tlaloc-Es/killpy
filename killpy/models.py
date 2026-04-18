"""
Core data models for killpy.

All detectors produce :class:`Environment` instances; the TUI and CLI
commands consume them.  Using a proper dataclass instead of raw tuples
makes the contract between layers explicit and IDE-friendly.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Literal

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


# ---------------------------------------------------------------------------
# Intelligence layer models
# ---------------------------------------------------------------------------


@dataclass
class GitInfo:
    """Git repository metadata for an environment's parent project."""

    is_git_repo: bool
    is_active: bool
    last_commit: datetime | None = None
    repo_root: Path | None = None


@dataclass
class ScoredEnvironment:
    """An :class:`Environment` enriched with scoring metadata.

    Wraps the original environment via composition so that existing code
    consuming plain :class:`Environment` objects is unaffected.
    """

    env: Environment
    score: float  # 0.0 (keep) – 1.0 (delete)
    explanation: list[str] = field(default_factory=list)
    git_info: GitInfo | None = None
    has_project_files: bool = False
    is_orphan: bool = False
    num_packages: int = 0


@dataclass
class Suggestion:
    """An actionable recommendation for a single environment."""

    env_path: Path
    score: float
    category: Literal["HIGH", "MEDIUM", "LOW"]
    reasons: list[str]
    recommended_action: str


@dataclass
class ScanRecord:
    """A persisted snapshot of one scan session."""

    timestamp: datetime
    total_space_found: int
    total_space_deleted: int
    environments_count: int
    scan_path: str

    def to_dict(self) -> dict:
        return {
            "timestamp": self.timestamp.isoformat(),
            "total_space_found": self.total_space_found,
            "total_space_deleted": self.total_space_deleted,
            "environments_count": self.environments_count,
            "scan_path": self.scan_path,
        }

    @classmethod
    def from_dict(cls, data: dict) -> ScanRecord:
        return cls(
            timestamp=datetime.fromisoformat(data["timestamp"]),
            total_space_found=data["total_space_found"],
            total_space_deleted=data["total_space_deleted"],
            environments_count=data["environments_count"],
            scan_path=data["scan_path"],
        )
