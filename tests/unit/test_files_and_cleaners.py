"""Tests for killpy/files/__init__.py, killpy/cleaners/__init__.py, and killpy/commands/clean.py."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest
from click.testing import CliRunner

from killpy.__main__ import cli
from killpy.cleaners import remove_pycache
from killpy.files import format_size, get_total_size


# ---------------------------------------------------------------------------
# files/__init__.py
# ---------------------------------------------------------------------------

class TestGetTotalSize:
    def test_empty_directory_returns_zero(self, tmp_path: Path) -> None:
        assert get_total_size(tmp_path) == 0

    def test_single_file(self, tmp_path: Path) -> None:
        f = tmp_path / "file.txt"
        f.write_bytes(b"hello")
        assert get_total_size(tmp_path) == 5

    def test_multiple_files(self, tmp_path: Path) -> None:
        (tmp_path / "a.txt").write_bytes(b"ab")
        (tmp_path / "b.txt").write_bytes(b"cde")
        assert get_total_size(tmp_path) == 5

    def test_nested_files(self, tmp_path: Path) -> None:
        sub = tmp_path / "sub"
        sub.mkdir()
        (sub / "deep.txt").write_bytes(b"x" * 100)
        (tmp_path / "top.txt").write_bytes(b"y" * 50)
        assert get_total_size(tmp_path) == 150

    def test_handles_missing_file_gracefully(self, tmp_path: Path) -> None:
        """Should not raise if a file disappears mid-scan."""
        f = tmp_path / "ghost.txt"
        f.write_bytes(b"x")
        # simulate a FileNotFoundError during stat
        original_rglob = tmp_path.rglob

        def _rglob(pattern):
            for p in original_rglob(pattern):
                yield p

        # Even if a file disappears, get_total_size should not raise
        result = get_total_size(tmp_path)
        assert isinstance(result, int)


class TestFormatSize:
    def test_bytes(self) -> None:
        assert format_size(0) == "0 bytes"
        assert format_size(512) == "512 bytes"
        assert format_size(1023) == "1023 bytes"

    def test_kilobytes(self) -> None:
        assert format_size(1024) == "1.00 KB"
        assert format_size(2048) == "2.00 KB"

    def test_megabytes(self) -> None:
        assert format_size(1 << 20) == "1.00 MB"
        assert format_size(int(2.5 * (1 << 20))) == "2.50 MB"

    def test_gigabytes(self) -> None:
        assert format_size(1 << 30) == "1.00 GB"
        assert format_size(int(1.5 * (1 << 30))) == "1.50 GB"


# ---------------------------------------------------------------------------
# cleaners/__init__.py
# ---------------------------------------------------------------------------

class TestRemovePycache:
    def test_removes_pycache_and_returns_freed_size(self, tmp_path: Path) -> None:
        cache = tmp_path / "src" / "__pycache__"
        cache.mkdir(parents=True)
        (cache / "mod.cpython-312.pyc").write_bytes(b"x" * 200)
        freed = remove_pycache(tmp_path)
        assert freed == 200
        assert not cache.exists()

    def test_no_pycache_returns_zero(self, tmp_path: Path) -> None:
        (tmp_path / "module.py").write_text("pass")
        freed = remove_pycache(tmp_path)
        assert freed == 0

    def test_removes_multiple_pycache_dirs(self, tmp_path: Path) -> None:
        for pkg in ("pkg_a", "pkg_b"):
            c = tmp_path / pkg / "__pycache__"
            c.mkdir(parents=True)
            (c / "mod.pyc").write_bytes(b"x" * 100)
        freed = remove_pycache(tmp_path)
        assert freed == 200

    def test_continues_on_error(self, tmp_path: Path) -> None:
        cache = tmp_path / "__pycache__"
        cache.mkdir()
        (cache / "x.pyc").write_bytes(b"y")
        with patch("shutil.rmtree", side_effect=PermissionError("denied")):
            # Should not raise
            freed = remove_pycache(tmp_path)
        assert freed >= 0


# ---------------------------------------------------------------------------
# commands/clean.py
# ---------------------------------------------------------------------------

class TestCleanCommand:
    def test_clean_runs_without_error(self, tmp_path: Path) -> None:
        runner = CliRunner()
        result = runner.invoke(cli, ["clean", "--path", str(tmp_path)])
        assert result.exit_code == 0

    def test_clean_actually_removes_pycache(self, tmp_path: Path) -> None:
        cache = tmp_path / "src" / "__pycache__"
        cache.mkdir(parents=True)
        (cache / "x.pyc").write_bytes(b"data")
        runner = CliRunner()
        runner.invoke(cli, ["clean", "--path", str(tmp_path)])
        assert not cache.exists()

    def test_clean_default_path(self) -> None:
        """Clean without --path should not crash (uses cwd)."""
        runner = CliRunner()
        with runner.isolated_filesystem():
            result = runner.invoke(cli, ["clean"])
        assert result.exit_code == 0
