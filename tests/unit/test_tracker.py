"""Unit tests for ``killpy.intelligence.tracker``."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from killpy.intelligence.tracker import UsageTracker
from killpy.models import ScanRecord

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _record(
    timestamp: datetime | None = None,
    space_found: int = 1_000_000,
    space_deleted: int = 500_000,
    count: int = 3,
    scan_path: str = "/tmp",
) -> ScanRecord:
    return ScanRecord(
        timestamp=timestamp or datetime(2024, 6, 1, tzinfo=timezone.utc),
        total_space_found=space_found,
        total_space_deleted=space_deleted,
        environments_count=count,
        scan_path=scan_path,
    )


# ---------------------------------------------------------------------------
# Basic read/write
# ---------------------------------------------------------------------------


class TestRecordScan:
    def test_creates_history_file(self, tmp_path: Path) -> None:
        tracker = UsageTracker(tmp_path / "history.json")
        tracker.record_scan(_record())
        assert (tmp_path / "history.json").exists()

    def test_roundtrip(self, tmp_path: Path) -> None:
        tracker = UsageTracker(tmp_path / "history.json")
        r = _record()
        tracker.record_scan(r)
        history = tracker.get_history()
        assert len(history) == 1
        assert history[0].environments_count == r.environments_count
        assert history[0].scan_path == r.scan_path

    def test_multiple_records_accumulated(self, tmp_path: Path) -> None:
        tracker = UsageTracker(tmp_path / "history.json")
        for i in range(3):
            tracker.record_scan(_record(count=i + 1))
        assert len(tracker.get_history()) == 3


# ---------------------------------------------------------------------------
# record_deletion
# ---------------------------------------------------------------------------


class TestRecordDeletion:
    def test_increments_deleted_field(self, tmp_path: Path) -> None:
        tracker = UsageTracker(tmp_path / "history.json")
        tracker.record_scan(_record(space_deleted=0))
        tracker.record_deletion(999)
        history = tracker.get_history()
        assert history[-1].total_space_deleted == 999

    def test_noop_when_no_history(self, tmp_path: Path) -> None:
        tracker = UsageTracker(tmp_path / "history.json")
        # Should not raise
        tracker.record_deletion(123)


# ---------------------------------------------------------------------------
# get_summary
# ---------------------------------------------------------------------------


class TestGetSummary:
    def test_empty_summary_when_no_history(self, tmp_path: Path) -> None:
        tracker = UsageTracker(tmp_path / "history.json")
        summary = tracker.get_summary()
        assert summary["total_scans"] == 0
        assert summary["total_space_found"] == 0

    def test_cumulative_totals(self, tmp_path: Path) -> None:
        tracker = UsageTracker(tmp_path / "history.json")
        tracker.record_scan(_record(space_found=1_000, space_deleted=400))
        tracker.record_scan(_record(space_found=2_000, space_deleted=600))
        summary = tracker.get_summary()
        assert summary["total_scans"] == 2
        assert summary["total_space_found"] == 3_000
        assert summary["total_space_deleted"] == 1_000

    def test_last_scan_time_set(self, tmp_path: Path) -> None:
        tracker = UsageTracker(tmp_path / "history.json")
        tracker.record_scan(_record())
        summary = tracker.get_summary()
        assert summary["last_scan_time"] is not None


# ---------------------------------------------------------------------------
# Corrupt JSON recovery
# ---------------------------------------------------------------------------


class TestCorruptJsonRecovery:
    def test_corrupt_file_resets(self, tmp_path: Path) -> None:
        path = tmp_path / "history.json"
        path.write_text("{not valid json}", encoding="utf-8")
        tracker = UsageTracker(path)
        # Should not raise; silently returns empty
        history = tracker.get_history()
        assert history == []

    def test_wrong_json_type_resets(self, tmp_path: Path) -> None:
        path = tmp_path / "history.json"
        path.write_text(json.dumps({"key": "value"}), encoding="utf-8")
        tracker = UsageTracker(path)
        history = tracker.get_history()
        assert history == []


# ---------------------------------------------------------------------------
# Atomic write / directory creation
# ---------------------------------------------------------------------------


class TestAtomicWrite:
    def test_creates_nested_directories(self, tmp_path: Path) -> None:
        deep = tmp_path / "a" / "b" / "c" / "history.json"
        tracker = UsageTracker(deep)
        tracker.record_scan(_record())
        assert deep.exists()

    def test_existing_file_is_replaced(self, tmp_path: Path) -> None:
        path = tmp_path / "history.json"
        tracker = UsageTracker(path)
        tracker.record_scan(_record(count=1))
        tracker.record_scan(_record(count=2))
        history = tracker.get_history()
        assert len(history) == 2
