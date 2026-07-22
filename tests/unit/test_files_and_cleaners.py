"""Tests for killpy/files/__init__.py, killpy/cleaners/__init__.py, and clean.py."""

from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import patch

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

    def test_skips_files_that_vanish_mid_scan(self, tmp_path: Path) -> None:
        """A file that vanishes between listing and stat is skipped, not raised on."""
        (tmp_path / "ghost.txt").write_bytes(b"x" * 100)
        (tmp_path / "real.txt").write_bytes(b"y" * 50)
        real_lstat = os.lstat

        def flaky_lstat(path, *args, **kwargs):
            if str(path).endswith("ghost.txt"):
                raise OSError("vanished")
            return real_lstat(path, *args, **kwargs)

        with patch("killpy.files.os.lstat", side_effect=flaky_lstat):
            result = get_total_size(tmp_path)
        assert result == 50  # ghost skipped (OSError), real.txt still counted

    def test_does_not_follow_directory_symlinks(self, tmp_path: Path) -> None:
        """A symlinked directory inside the tree must not pull in outside
        content (guards against pathlib ``**`` symlink-following semantics,
        which varied across Python versions)."""
        outside = tmp_path / "outside"
        outside.mkdir()
        (outside / "big.bin").write_bytes(b"x" * 10_000)
        tree = tmp_path / "tree"
        tree.mkdir()
        (tree / "own.txt").write_bytes(b"y" * 100)
        (tree / "link").symlink_to(outside, target_is_directory=True)

        total = get_total_size(tree)

        assert 100 <= total < 10_000

    def test_counts_file_symlink_as_link_not_target(self, tmp_path: Path) -> None:
        """Regression: is_file()/stat() followed file symlinks, so a link
        into a large file outside the env inflated its reported size."""
        target = tmp_path / "target.bin"
        target.write_bytes(b"x" * 10_000)
        tree = tmp_path / "tree"
        tree.mkdir()
        (tree / "link.bin").symlink_to(target)

        assert get_total_size(tree) < 10_000


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
            # Should not raise, and a failed removal frees nothing
            freed = remove_pycache(tmp_path)
        assert freed == 0

    def test_does_not_delete_through_directory_symlink(self, tmp_path: Path) -> None:
        """A symlinked dir inside the tree must never expose outside caches
        to deletion, regardless of the interpreter's glob semantics."""
        outside = tmp_path / "outside"
        pycache_outside = outside / "__pycache__"
        pycache_outside.mkdir(parents=True)
        (pycache_outside / "x.pyc").write_bytes(b"z")
        tree = tmp_path / "tree"
        tree.mkdir()
        (tree / "link").symlink_to(outside, target_is_directory=True)

        freed = remove_pycache(tree)

        assert freed == 0
        assert pycache_outside.exists()

    def test_skips_symlink_named_pycache(self, tmp_path: Path) -> None:
        """Regression: a symlink named __pycache__ had its target's content
        counted as freed space (and was handed to rmtree)."""
        target = tmp_path / "real-dir"
        target.mkdir()
        (target / "data.txt").write_bytes(b"important")
        tree = tmp_path / "tree"
        tree.mkdir()
        (tree / "__pycache__").symlink_to(target, target_is_directory=True)

        freed = remove_pycache(tree)

        assert freed == 0
        assert (target / "data.txt").exists()


# ---------------------------------------------------------------------------
# commands/clean.py
# ---------------------------------------------------------------------------


class TestCleanCommand:
    def test_clean_actually_removes_pycache(self, tmp_path: Path) -> None:
        cache = tmp_path / "src" / "__pycache__"
        cache.mkdir(parents=True)
        (cache / "x.pyc").write_bytes(b"data")
        runner = CliRunner()
        result = runner.invoke(cli, ["clean", "--path", str(tmp_path)])
        assert result.exit_code == 0
        assert not cache.exists()

    def test_clean_default_path(self) -> None:
        """Clean without --path should not crash (uses cwd)."""
        runner = CliRunner()
        with runner.isolated_filesystem():
            result = runner.invoke(cli, ["clean"])
        assert result.exit_code == 0

    def test_clean_rejects_nonexistent_path(self, tmp_path: Path) -> None:
        """A typo'd path must be a usage error, not a silent '0 bytes freed'."""
        runner = CliRunner()
        result = runner.invoke(cli, ["clean", "--path", str(tmp_path / "missing")])
        assert result.exit_code == 2
        assert "does not exist" in result.output
