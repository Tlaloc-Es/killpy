"""Unit tests for individual detectors.

Each detector is exercised against a synthetic filesystem built with
``tmp_path`` so that no real environments need to be present on the machine.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from unittest.mock import patch

import pytest

from killpy.detectors.venv import VenvDetector
from killpy.detectors import venv as venv_mod
from killpy.detectors.pyenv import PyenvDetector, _pyenv_versions_root
from killpy.detectors.cache import CacheDetector
from killpy.models import Environment


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_venv(root: Path, name: str = ".venv") -> Path:
    """Create a minimal venv directory (pyvenv.cfg marker)."""
    venv = root / name
    venv.mkdir(parents=True)
    (venv / "pyvenv.cfg").write_text("home = /usr/bin\n")
    return venv


def _make_pycache(root: Path, parent: str = "src") -> Path:
    """Create a __pycache__ directory with a dummy .pyc file."""
    cache = root / parent / "__pycache__"
    cache.mkdir(parents=True, exist_ok=True)
    (cache / "dummy.cpython-312.pyc").write_bytes(b"\x00" * 100)
    return cache


# ---------------------------------------------------------------------------
# VenvDetector
# ---------------------------------------------------------------------------

class TestVenvDetector:
    def test_finds_named_venv(self, tmp_path: Path) -> None:
        _make_venv(tmp_path)
        detector = VenvDetector()
        envs = detector.detect(tmp_path)
        assert len(envs) == 1
        # VenvDetector stores the full path string as name
        assert envs[0].path.name == ".venv"
        assert envs[0].type == ".venv"

    def test_finds_pyvenv_cfg_dir(self, tmp_path: Path) -> None:
        """A directory that contains pyvenv.cfg (but is not named .venv)."""
        custom = tmp_path / "myenv"
        custom.mkdir()
        (custom / "pyvenv.cfg").write_text("home = /usr/bin\n")
        detector = VenvDetector()
        envs = detector.detect(tmp_path)
        # name stores full path; compare using path.name
        found_dir_names = {e.path.name for e in envs}
        assert "myenv" in found_dir_names

    def test_deduplicates_when_venv_has_pyvenv_cfg(self, tmp_path: Path) -> None:
        """A .venv dir that also contains pyvenv.cfg should appear once."""
        _make_venv(tmp_path, ".venv")
        detector = VenvDetector()
        envs = detector.detect(tmp_path)
        venv_paths = [e.path for e in envs]
        # No duplicates
        assert len(venv_paths) == len(set(venv_paths))

    def test_no_envs_in_empty_dir(self, tmp_path: Path) -> None:
        detector = VenvDetector()
        envs = detector.detect(tmp_path)
        assert envs == []

    def test_multiple_venvs(self, tmp_path: Path) -> None:
        proj_a = tmp_path / "project_a"
        proj_b = tmp_path / "project_b"
        _make_venv(proj_a)
        _make_venv(proj_b)
        detector = VenvDetector()
        envs = detector.detect(tmp_path)
        assert len(envs) == 2

    def test_can_handle_always_true(self) -> None:
        assert VenvDetector().can_handle() is True

    def test_env_fields_are_populated(self, tmp_path: Path) -> None:
        _make_venv(tmp_path)
        detector = VenvDetector()
        envs = detector.detect(tmp_path)
        env = envs[0]
        assert isinstance(env, Environment)
        assert isinstance(env.path, Path)
        assert isinstance(env.last_accessed, datetime)
        assert env.size_bytes >= 0
        assert env.size_human  # non-empty string

    def test_skips_excluded_dirs(self, tmp_path: Path) -> None:
        """Directories like node_modules / .git should not be walked."""
        excluded = tmp_path / "node_modules" / ".venv"
        excluded.mkdir(parents=True)
        (excluded / "pyvenv.cfg").write_text("home = /usr/bin\n")
        detector = VenvDetector()
        envs = detector.detect(tmp_path)
        assert envs == []

    def test_deduplicates_via_symlink_hits_continue(self, tmp_path: Path) -> None:
        """Two .venv paths resolving to the same realpath → second skipped (line 74)."""
        real_venv = tmp_path / "a" / ".venv"
        real_venv.mkdir(parents=True)
        link_venv = tmp_path / "b" / ".venv"
        link_venv.parent.mkdir()
        link_venv.symlink_to(real_venv)  # b/.venv -> a/.venv (same resolved path)
        envs = VenvDetector().detect(tmp_path)
        assert len(envs) == 1

    def test_skips_venv_when_resolve_raises(self, tmp_path: Path) -> None:
        """Non-existent .venv fed into loop1 → resolve(strict=True) raises (lines 77-78)."""
        ghost = tmp_path / ".venv"  # does NOT exist on disk
        with patch.object(venv_mod, "_iter_dirs_named", return_value=iter([ghost])):
            envs = VenvDetector().detect(tmp_path)
        assert envs == []

    def test_skips_pyvenv_cfg_when_resolve_raises(self, tmp_path: Path) -> None:
        """Non-existent venv_dir from pyvenv.cfg loop → resolve raises (lines 89-90)."""
        ghost_cfg = tmp_path / "ghost" / "pyvenv.cfg"  # parent doesn't exist
        with patch.object(venv_mod, "_iter_files_named", return_value=iter([ghost_cfg])):
            envs = VenvDetector().detect(tmp_path)
        assert envs == []


# ---------------------------------------------------------------------------
# PyenvDetector
# ---------------------------------------------------------------------------

class TestPyenvDetector:
    def _fake_versions_root(self, tmp_path: Path) -> Path:
        versions = tmp_path / "pyenv" / "versions"
        versions.mkdir(parents=True)
        (versions / "3.11.0").mkdir()
        (versions / "3.12.1").mkdir()
        return versions

    def test_finds_pyenv_versions(self, tmp_path: Path) -> None:
        versions_root = self._fake_versions_root(tmp_path)
        with patch("killpy.detectors.pyenv._pyenv_versions_root", return_value=versions_root):
            detector = PyenvDetector()
            envs = detector.detect(tmp_path)
        assert len(envs) == 2
        names = {e.name for e in envs}
        assert "3.11.0" in names
        assert "3.12.1" in names

    def test_returns_empty_when_no_versions(self, tmp_path: Path) -> None:
        versions_root = tmp_path / "pyenv" / "versions"
        versions_root.mkdir(parents=True)
        with patch("killpy.detectors.pyenv._pyenv_versions_root", return_value=versions_root):
            detector = PyenvDetector()
            envs = detector.detect(tmp_path)
        assert envs == []

    def test_can_handle_true_when_dir_exists(self, tmp_path: Path) -> None:
        versions_root = self._fake_versions_root(tmp_path)
        with patch("killpy.detectors.pyenv._pyenv_versions_root", return_value=versions_root):
            detector = PyenvDetector()
            assert detector.can_handle() is True

    def test_can_handle_false_when_dir_missing(self, tmp_path: Path) -> None:
        missing = tmp_path / "pyenv" / "versions"
        with patch("killpy.detectors.pyenv._pyenv_versions_root", return_value=missing):
            detector = PyenvDetector()
            assert detector.can_handle() is False

    def test_env_type_is_pyenv(self, tmp_path: Path) -> None:
        versions_root = self._fake_versions_root(tmp_path)
        with patch("killpy.detectors.pyenv._pyenv_versions_root", return_value=versions_root):
            detector = PyenvDetector()
            envs = detector.detect(tmp_path)
        assert all(e.type == "pyenv" for e in envs)


# ---------------------------------------------------------------------------
# CacheDetector
# ---------------------------------------------------------------------------

class TestCacheDetector:
    def test_finds_pycache(self, tmp_path: Path) -> None:
        _make_pycache(tmp_path)
        detector = CacheDetector()
        # _scan_local uses the dir name as type (e.g. "__pycache__")
        local = detector._scan_local(tmp_path)
        assert len(local) >= 1
        assert any("pycache" in e.type for e in local)

    def test_no_cache_in_clean_dir(self, tmp_path: Path) -> None:
        detector = CacheDetector()
        # Test only local scan so global pip/uv caches don't interfere
        local = detector._scan_local(tmp_path)
        assert local == []

    def test_can_handle_always_true(self) -> None:
        assert CacheDetector().can_handle() is True
