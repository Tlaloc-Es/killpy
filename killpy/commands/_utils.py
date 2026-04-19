"""Shared helpers for ``killpy`` commands."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from killpy.models import Environment


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
        matches one of these strings (case-insensitive) are kept.
    older_than:
        If provided, only environments not accessed in the last *older_than* days
        are kept.
    """
    now = datetime.now(tz=timezone.utc)
    result = envs

    if types:
        type_set = {t.strip().lower() for t in types}
        result = [e for e in result if e.type.lower() in type_set]

    if older_than is not None:
        cutoff = now - timedelta(days=older_than)
        result = [e for e in result if e.last_accessed < cutoff]

    return result
