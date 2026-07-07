"""Shared helpers for ``killpy`` commands."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from rich.console import Console

from killpy.models import Environment

# Maps user-facing type names (detector names) to the concrete ``Environment.type``
# values those detectors produce.  Two detectors use sub-type tags instead of
# their own name: VenvDetector (tags: ".venv", "pyvenv.cfg") and CacheDetector
# (tags: "__pycache__", ".mypy_cache", ".pytest_cache", ".ruff_cache",
# "pip-cache", "uv-cache").  Without this mapping, ``--type venv`` and
# ``--type cache`` would never match anything.
_TYPE_ALIASES: dict[str, frozenset[str]] = {
    "venv": frozenset({".venv", "pyvenv.cfg"}),
    "cache": frozenset(
        {
            "__pycache__",
            ".mypy_cache",
            ".pytest_cache",
            ".ruff_cache",
            "pip-cache",
            "uv-cache",
        }
    ),
}


def partition_in_use(
    envs: list[Environment], force: bool, console: Console
) -> list[Environment]:
    """Drop in-use (system-critical) environments unless *force*, reporting skips.

    Returns the environments that are safe to delete.  When *force* is
    ``True`` the list is returned unchanged.
    """
    if force:
        return envs
    protected = [e for e in envs if e.is_system_critical]
    if not protected:
        return envs
    console.print(
        f"\n[yellow]Skipping {len(protected)} environment(s) currently in use"
        " — pass --force to include them:[/yellow]"
    )
    for env in protected:
        console.print(f"  [dim]⚠ {env.path}[/dim]")
    return [e for e in envs if not e.is_system_critical]


def filter_envs(
    envs: list[Environment],
    types: tuple[str, ...] | None,
    older_than: int | None,
) -> list[Environment]:
    """Return a filtered subset of *envs*.

    Parameters
    ----------
    envs:
        Full list of detected environments.
    types:
        If provided, only environments whose :attr:`~killpy.models.Environment.type`
        matches one of these strings (case-insensitive) are kept.  Detector
        names such as ``"venv"`` and ``"cache"`` are automatically expanded to
        their concrete sub-type values via :data:`_TYPE_ALIASES`.
    older_than:
        If provided, only environments not accessed in the last *older_than* days
        are kept.
    """
    now = datetime.now(tz=timezone.utc)
    result = envs

    if types:
        expanded: set[str] = set()
        for t in types:
            t_lower = t.strip().lower()
            expanded.add(t_lower)
            expanded.update(_TYPE_ALIASES.get(t_lower, frozenset()))
        result = [e for e in result if e.type.lower() in expanded]

    if older_than is not None:
        cutoff = now - timedelta(days=older_than)
        result = [e for e in result if e.last_accessed < cutoff]

    return result
