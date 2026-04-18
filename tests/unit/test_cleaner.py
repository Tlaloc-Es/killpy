"""Unit tests for Cleaner.

All destructive calls (shutil.rmtree, subprocess.run) are mocked so that
the tests never touch the real filesystem or spawn subprocesses.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from killpy.cleaner import Cleaner, CleanerError
from killpy.models import Environment

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _env(
    path: Path | None = None,
    name: str = "myenv",
    env_type: str = "venv",
    size: int = 2048,
    managed_by: str | None = None,
) -> Environment:
    return Environment(
        path=path or Path("/fake/env"),
        name=name,
        type=env_type,
        last_accessed=datetime(2024, 6, 1, tzinfo=timezone.utc),
        size_bytes=size,
        managed_by=managed_by,
    )


# ---------------------------------------------------------------------------
# Dry-run mode
# ---------------------------------------------------------------------------


class TestCleanerDryRun:
    def test_dry_run_returns_size_without_deleting(self, tmp_path: Path) -> None:
        env = _env(path=tmp_path / "env", size=5000)
        cleaner = Cleaner(dry_run=True)
        with patch("shutil.rmtree") as mock_rm:
            freed = cleaner.delete(env)
        assert freed == 5000
        mock_rm.assert_not_called()

    def test_dry_run_delete_many_accumulates_size(self, tmp_path: Path) -> None:
        envs = [_env(path=tmp_path / f"env{i}", size=1000) for i in range(3)]
        cleaner = Cleaner(dry_run=True)
        with patch("shutil.rmtree"):
            total = cleaner.delete_many(envs)
        assert total == 3000


# ---------------------------------------------------------------------------
# Filesystem deletion
# ---------------------------------------------------------------------------


class TestCleanerFilesystem:
    def test_deletes_via_rmtree(self, tmp_path: Path) -> None:
        env_path = tmp_path / "myenv"
        env_path.mkdir()
        env = _env(path=env_path, size=100)
        cleaner = Cleaner()
        freed = cleaner.delete(env)
        assert freed == 100
        assert not env_path.exists()

    def test_missing_path_does_not_raise(self, tmp_path: Path) -> None:
        env = _env(path=tmp_path / "nonexistent", size=50)
        cleaner = Cleaner()
        # Should log a warning and return the size without raising
        freed = cleaner.delete(env)
        assert freed == 50

    def test_delete_many_returns_total_freed(self, tmp_path: Path) -> None:
        dirs = []
        for i in range(3):
            d = tmp_path / f"env{i}"
            d.mkdir()
            dirs.append(d)
        envs = [_env(path=d, size=500) for d in dirs]
        cleaner = Cleaner()
        total = cleaner.delete_many(envs)
        assert total == 1500

    def test_delete_many_on_progress_called(self, tmp_path: Path) -> None:
        d = tmp_path / "env"
        d.mkdir()
        env = _env(path=d, size=300)
        progress_calls: list = []
        cleaner = Cleaner()
        cleaner.delete_many(
            [env],
            on_progress=lambda e, freed, total: progress_calls.append((freed, total)),
        )
        assert progress_calls == [(300, 300)]


# ---------------------------------------------------------------------------
# Conda environments
# ---------------------------------------------------------------------------


class TestCleanerConda:
    def test_calls_conda_env_remove(self) -> None:
        env = _env(name="myenv", managed_by="conda")
        with (
            patch("shutil.which", return_value="/usr/bin/conda"),
            patch("subprocess.run") as mock_run,
        ):
            mock_run.return_value = MagicMock(returncode=0)
            cleaner = Cleaner()
            freed = cleaner.delete(env)
        assert freed == env.size_bytes
        mock_run.assert_called_once()
        args = mock_run.call_args[0][0]
        assert "conda" in args
        assert "myenv" in args

    def test_raises_when_conda_not_found(self) -> None:
        env = _env(name="myenv", managed_by="conda")
        with patch("shutil.which", return_value=None):
            cleaner = Cleaner()
            with pytest.raises(CleanerError, match="conda not found"):
                cleaner.delete(env)

    def test_raises_when_conda_fails(self) -> None:
        env = _env(name="myenv", managed_by="conda")
        with (
            patch("shutil.which", return_value="/usr/bin/conda"),
            patch("subprocess.run") as mock_run,
        ):
            mock_run.return_value = MagicMock(returncode=1, stderr="some error")
            cleaner = Cleaner()
            with pytest.raises(CleanerError, match="conda env remove failed"):
                cleaner.delete(env)


# ---------------------------------------------------------------------------
# pipx packages
# ---------------------------------------------------------------------------


class TestCleanerPipx:
    def test_calls_pipx_uninstall(self) -> None:
        env = _env(name="black", managed_by="pipx")
        with (
            patch("shutil.which", return_value="/usr/bin/pipx"),
            patch("subprocess.run") as mock_run,
        ):
            mock_run.return_value = MagicMock(returncode=0)
            cleaner = Cleaner()
            freed = cleaner.delete(env)
        assert freed == env.size_bytes
        args = mock_run.call_args[0][0]
        assert "pipx" in args
        assert "black" in args

    def test_raises_when_pipx_not_found(self) -> None:
        env = _env(name="black", managed_by="pipx")
        with patch("shutil.which", return_value=None):
            cleaner = Cleaner()
            with pytest.raises(CleanerError, match="pipx not found"):
                cleaner.delete(env)

    def test_raises_when_pipx_fails(self) -> None:
        env = _env(name="black", managed_by="pipx")
        with (
            patch("shutil.which", return_value="/usr/bin/pipx"),
            patch("subprocess.run") as mock_run,
        ):
            mock_run.return_value = MagicMock(returncode=1, stderr="error")
            cleaner = Cleaner()
            with pytest.raises(CleanerError, match="pipx uninstall failed"):
                cleaner.delete(env)


# ---------------------------------------------------------------------------
# delete_many error handling
# ---------------------------------------------------------------------------


class TestCleanerDeleteManyErrors:
    def test_continues_after_individual_error(self, tmp_path: Path) -> None:
        """A failed deletion for one env should not abort the rest."""
        good = tmp_path / "good"
        good.mkdir()
        bad = tmp_path / "bad"
        bad.mkdir()

        envs = [
            _env(path=bad, name="bad", managed_by="conda"),
            _env(path=good, size=200),
        ]
        with (
            patch("shutil.which", return_value=None),  # conda not found
        ):
            cleaner = Cleaner()
            total = cleaner.delete_many(envs)
        # Second env deleted, first failed
        assert total == 200
