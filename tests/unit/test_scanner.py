"""Unit tests for Scanner.

The scanner is tested by injecting stub detectors so that no real
filesystem access is required.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from killpy.detectors.base import AbstractDetector
from killpy.models import Environment
from killpy.scanner import Scanner


# ---------------------------------------------------------------------------
# Fixtures / stubs
# ---------------------------------------------------------------------------

def _make_env(path: Path, env_type: str = "venv", size: int = 1024) -> Environment:
    return Environment(
        path=path,
        name=path.name,
        type=env_type,
        last_accessed=datetime(2024, 1, 1),
        size_bytes=size,
    )


def _stub_detector(
    name: str,
    envs: list[Environment],
    can_handle: bool = True,
) -> AbstractDetector:
    d = MagicMock(spec=AbstractDetector)
    d.name = name
    d.can_handle.return_value = can_handle
    d.detect.return_value = envs
    return d


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestScanner:
    def test_returns_environments_from_single_detector(self, tmp_path: Path) -> None:
        env = _make_env(tmp_path / "project" / ".venv")
        stub = _stub_detector("venv", [env])
        scanner = Scanner(detectors=[stub])
        results = scanner.scan(tmp_path)
        assert len(results) == 1
        assert results[0] is env

    def test_aggregates_from_multiple_detectors(self, tmp_path: Path) -> None:
        env_a = _make_env(tmp_path / "a" / ".venv", "venv")
        env_b = _make_env(tmp_path / "b", "conda")
        scanner = Scanner(detectors=[
            _stub_detector("venv", [env_a]),
            _stub_detector("conda", [env_b]),
        ])
        results = scanner.scan(tmp_path)
        assert len(results) == 2

    def test_deduplicates_by_resolved_path(self, tmp_path: Path) -> None:
        """Two detectors returning the same resolved path → one result."""
        shared = tmp_path / "shared" / ".venv"
        shared.mkdir(parents=True)
        env_a = _make_env(shared, "venv")
        env_b = _make_env(shared, "pyenv")  # same path, different detector
        scanner = Scanner(detectors=[
            _stub_detector("venv", [env_a]),
            _stub_detector("pyenv", [env_b]),
        ])
        results = scanner.scan(tmp_path)
        assert len(results) == 1

    def test_skips_detectors_with_can_handle_false(self, tmp_path: Path) -> None:
        env = _make_env(tmp_path / ".venv")
        stub = _stub_detector("conda", [env], can_handle=False)
        scanner = Scanner(detectors=[stub])
        results = scanner.scan(tmp_path)
        assert results == []
        stub.detect.assert_not_called()

    def test_sorts_results_by_size_descending(self, tmp_path: Path) -> None:
        small = _make_env(tmp_path / "small" / ".venv", size=100)
        large = _make_env(tmp_path / "large" / ".venv", size=9999)
        scanner = Scanner(detectors=[
            _stub_detector("venv", [small, large]),
        ])
        results = scanner.scan(tmp_path)
        assert results[0].size_bytes == 9999
        assert results[1].size_bytes == 100

    def test_type_filter_keeps_matching(self, tmp_path: Path) -> None:
        env_venv = _make_env(tmp_path / "a" / ".venv", "venv")
        env_conda = _make_env(tmp_path / "b", "conda")
        scanner = Scanner(
            detectors=[
                _stub_detector("venv", [env_venv]),
                _stub_detector("conda", [env_conda]),
            ],
            types={"venv"},
        )
        results = scanner.scan(tmp_path)
        assert all(e.type == "venv" for e in results)

    def test_type_filter_excludes_others(self, tmp_path: Path) -> None:
        env_conda = _make_env(tmp_path / "conda_env", "conda")
        scanner = Scanner(
            detectors=[
                _stub_detector("venv", []),
                _stub_detector("conda", [env_conda]),
            ],
            types={"venv"},
        )
        results = scanner.scan(tmp_path)
        assert results == []

    def test_faulty_detector_does_not_stop_others(self, tmp_path: Path) -> None:
        env = _make_env(tmp_path / ".venv")
        bad = _stub_detector("conda", [])
        bad.detect.side_effect = RuntimeError("boom")
        good = _stub_detector("venv", [env])
        scanner = Scanner(detectors=[bad, good])
        results = scanner.scan(tmp_path)
        assert len(results) == 1

    def test_on_progress_callback_called_per_detector(self, tmp_path: Path) -> None:
        env_a = _make_env(tmp_path / "a" / ".venv", "venv")
        env_b = _make_env(tmp_path / "b", "conda")
        calls: list = []
        scanner = Scanner(detectors=[
            _stub_detector("venv", [env_a]),
            _stub_detector("conda", [env_b]),
        ])
        scanner.scan(tmp_path, on_progress=lambda det, envs: calls.append(det.name))
        assert "venv" in calls
        assert "conda" in calls

    def test_empty_scan_returns_empty_list(self, tmp_path: Path) -> None:
        scanner = Scanner(detectors=[_stub_detector("venv", [])])
        assert scanner.scan(tmp_path) == []

    def test_default_instantiates_all_detectors(self) -> None:
        """Scanner() with no args instantiates all default detectors (covers line 50)."""
        scanner = Scanner()
        assert len(scanner._detectors) > 0

    def test_deduplicate_handles_os_error_fallback(self, tmp_path: Path) -> None:
        """_deduplicate should use raw path when resolve() raises OSError."""
        env = _make_env(tmp_path / "a" / ".venv")
        # path that does not exist yet — resolve can still work, but we test the
        # OSError branch by patching
        with patch.object(type(env.path), "resolve", side_effect=OSError):
            scanner = Scanner(detectors=[_stub_detector("venv", [env])])
            results = scanner.scan(tmp_path)
        assert len(results) == 1


class TestScannerAsync:
    def test_scan_async_yields_results(self, tmp_path: Path) -> None:
        import asyncio
        env = _make_env(tmp_path / "a" / ".venv", "venv")
        stub = _stub_detector("venv", [env])
        scanner = Scanner(detectors=[stub])

        async def _collect():
            results = []
            async for _det, envs in scanner.scan_async(tmp_path):
                results.extend(envs)
            return results

        results = asyncio.run(_collect())
        assert len(results) == 1

    def test_scan_async_skips_can_handle_false(self, tmp_path: Path) -> None:
        import asyncio
        stub = _stub_detector("conda", [_make_env(tmp_path / "e")], can_handle=False)
        scanner = Scanner(detectors=[stub])

        async def _collect():
            results = []
            async for _det, envs in scanner.scan_async(tmp_path):
                results.extend(envs)
            return results

        results = asyncio.run(_collect())
        assert results == []

    def test_scan_async_handles_detector_exception(self, tmp_path: Path) -> None:
        import asyncio
        bad = _stub_detector("conda", [])
        bad.detect.side_effect = RuntimeError("crash")
        good_env = _make_env(tmp_path / ".venv")
        good = _stub_detector("venv", [good_env])
        scanner = Scanner(detectors=[bad, good])

        async def _collect():
            results = []
            async for _det, envs in scanner.scan_async(tmp_path):
                results.extend(envs)
            return results

        results = asyncio.run(_collect())
        assert len(results) == 1

    def test_scan_async_deduplicates(self, tmp_path: Path) -> None:
        import asyncio
        shared = tmp_path / "shared" / ".venv"
        shared.mkdir(parents=True)
        env_a = _make_env(shared, "venv")
        env_b = _make_env(shared, "pyenv")
        scanner = Scanner(detectors=[
            _stub_detector("venv", [env_a]),
            _stub_detector("pyenv", [env_b]),
        ])

        async def _collect():
            results = []
            async for _det, envs in scanner.scan_async(tmp_path):
                results.extend(envs)
            return results

        results = asyncio.run(_collect())
        assert len(results) == 1
