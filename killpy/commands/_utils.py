"""Shared helpers for ``killpy`` commands."""

from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone

import click
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

_SIZE_UNITS = {
    "b": 1,
    "kb": 1 << 10,
    "mb": 1 << 20,
    "gb": 1 << 30,
    "tb": 1 << 40,
}
_SIZE_PATTERN = re.compile(r"(\d+(?:\.\d+)?)\s*([kmgt]?b)", re.IGNORECASE)


class SizeParamType(click.ParamType):
    """Convert human-readable byte sizes such as ``500MB`` or ``1.5GB``."""

    name = "SIZE"

    def convert(self, value, param, ctx):  # type: ignore[no-untyped-def]
        if isinstance(value, int):
            return value
        match = _SIZE_PATTERN.fullmatch(value.strip())
        if match is None:
            self.fail("must be a size such as 500MB, 1.5GB, or 200KB", param, ctx)
        amount, unit = match.groups()
        return int(float(amount) * _SIZE_UNITS[unit.lower()])


SIZE = SizeParamType()


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
    min_size: int | None = None,
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
        If provided, only environments not modified in the last *older_than* days
        are kept.
    min_size:
        If provided, only environments at least this many bytes large are kept.
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
        result = [e for e in result if e.last_modified < cutoff]

    if min_size is not None:
        result = [e for e in result if e.size_bytes >= min_size]

    return result


def sort_envs(
    envs: list[Environment],
    sort_by: str = "size",
    reverse: bool = False,
) -> list[Environment]:
    """Sort a list of environments by *sort_by* key.

    Parameters
    ----------
    envs:
        List of environments to sort.
    sort_by:
        Key to sort by: ``"size"`` (bytes), ``"date"`` (last modified time),
        or ``"name"`` (environment name). Case-insensitive.
    reverse:
        If ``True``, invert the default sort order for the chosen key.

    Returns
    -------
    list[Environment]
        A new list of sorted environments.
    """
    key = sort_by.lower()
    if key == "size":
        return sorted(envs, key=lambda e: e.size_bytes, reverse=not reverse)
    elif key == "date":
        return sorted(envs, key=lambda e: e.last_modified, reverse=not reverse)
    elif key == "name":
        return sorted(envs, key=lambda e: e.name.lower(), reverse=reverse)
    else:
        raise ValueError(
            f"Invalid sort key: {sort_by!r}. Must be 'size', 'date', or 'name'."
        )
