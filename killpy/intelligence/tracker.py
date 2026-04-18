"""Lightweight persistence layer: tracks scan history and reclaimed space."""

from __future__ import annotations

import json
import logging
import os
import tempfile
from pathlib import Path

from killpy.models import ScanRecord, ScoredEnvironment

logger = logging.getLogger(__name__)

_DEFAULT_STORAGE = Path.home() / ".killpy" / "history.json"


class UsageTracker:
    """Persist scan history to a JSON file in ``~/.killpy/``.

    All I/O is best-effort: failures are logged at DEBUG level and never
    propagated to the caller.
    """

    def __init__(self, storage_path: Path | None = None) -> None:
        self._path = storage_path or _DEFAULT_STORAGE

    # ------------------------------------------------------------------ #
    #  Write operations                                                    #
    # ------------------------------------------------------------------ #

    def record_scan(self, record: ScanRecord) -> None:
        """Append *record* to the history file."""
        history = self._load()
        history.append(record.to_dict())
        self._save(history)

    def record_deletion(self, size_bytes: int) -> None:
        """Increment the ``total_space_deleted`` counter of the last scan record."""
        history = self._load()
        if not history:
            return
        history[-1]["total_space_deleted"] = (
            history[-1].get("total_space_deleted", 0) + size_bytes
        )
        self._save(history)

    # ------------------------------------------------------------------ #
    #  Read operations                                                     #
    # ------------------------------------------------------------------ #

    def get_history(self) -> list[ScanRecord]:
        """Return all persisted scan records."""
        records: list[ScanRecord] = []
        for raw in self._load():
            try:
                records.append(ScanRecord.from_dict(raw))
            except (KeyError, ValueError) as exc:
                logger.debug("Skipping corrupt record: %s", exc)
        return records

    def get_summary(self) -> dict:
        """Return cumulative aggregates over the full scan history."""
        records = self.get_history()
        if not records:
            return {
                "total_scans": 0,
                "total_space_found": 0,
                "total_space_deleted": 0,
                "last_scan_time": None,
            }
        return {
            "total_scans": len(records),
            "total_space_found": sum(r.total_space_found for r in records),
            "total_space_deleted": sum(r.total_space_deleted for r in records),
            "last_scan_time": max(r.timestamp for r in records).isoformat(),
        }

    @staticmethod
    def get_top_offenders(
        scored_envs: list[ScoredEnvironment], n: int = 5
    ) -> list[ScoredEnvironment]:
        """Return the *n* environments with the highest deletion-priority score."""
        return sorted(scored_envs, key=lambda se: se.score, reverse=True)[:n]

    # ------------------------------------------------------------------ #
    #  Internal I/O                                                        #
    # ------------------------------------------------------------------ #

    def _load(self) -> list[dict]:
        if not self._path.exists():
            return []
        try:
            text = self._path.read_text(encoding="utf-8")
            data = json.loads(text)
            if not isinstance(data, list):
                raise ValueError("Expected a JSON list")
            return data
        except (json.JSONDecodeError, ValueError, OSError) as exc:
            logger.debug(
                "Could not load history from %s: %s — resetting", self._path, exc
            )
            return []

    def _save(self, history: list[dict]) -> None:
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            # Atomic write: write to a temp file then rename.
            fd, tmp = tempfile.mkstemp(
                dir=self._path.parent, prefix=".history_", suffix=".json"
            )
            try:
                with os.fdopen(fd, "w", encoding="utf-8") as fh:
                    json.dump(history, fh, indent=2, default=str)
                os.replace(tmp, self._path)
            except Exception:
                try:
                    os.unlink(tmp)
                except OSError:
                    pass
                raise
        except OSError as exc:
            logger.debug("Could not save history to %s: %s", self._path, exc)
