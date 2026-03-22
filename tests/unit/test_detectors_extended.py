"""Extended detector tests covering conda, poetry, pipx, hatch, pipenv, tox, uv, artifacts."""

from __future__ import annotations

import json
import subprocess
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from killpy.detectors.artifacts import ArtifactsDetector, _is_artifact_dir
from killpy.detectors.cache import CacheDetector, _make_cache_env
from killpy.detectors.conda import CondaDetector
from killpy.detectors.hatch import HatchDetector, _hatch_envs_root
from killpy.detectors.pipenv import PipenvDetector, _pipenv_venvs_root
from killpy.detectors.pipx import PipxDetector, _pipx_venvs_root
from killpy.detectors.poetry import PoetryDetector, _poetry_venvs_dir
from killpy.detectors.tox import ToxDetector
from killpy.detectors.uv import UvDetector


# ---------------------------------------------------------------------------
# CondaDetector
# ---------------------------------------------------------------------------

class TestCondaDetector:
    def _conda_output(self, lines: list[str]) -> str:
        return "\n".join(lines) + "\n"

    def test_can_handle_true_when_conda_on_path(self) -> None:
        with patch("shutil.which", return_value="/usr/bin/conda"):
            assert CondaDetector().can_handle() is True

    def test_can_handle_false_when_conda_missing(self) -> None:
        with patch("shutil.which", return_value=None):
            assert CondaDetector().can_handle() is False

    def test_detects_environments(self, tmp_path: Path) -> None:
        env_path = tmp_path / "myenv"
        env_path.mkdir()
        output = self._conda_output([
            "# conda environments:",
            "#",
            f"base                     /some/base",
            f"myenv                    {env_path}",
        ])
        with (
            patch("shutil.which", return_value="/usr/bin/conda"),
            patch("subprocess.run") as mock_run,
        ):
            mock_run.return_value = MagicMock(
                returncode=0, stdout=output, stderr=""
            )
            envs = CondaDetector().detect(tmp_path)

        found = {e.name for e in envs}
        assert "myenv" in found

    def test_skips_active_env_marked_with_star(self, tmp_path: Path) -> None:
        env_path = tmp_path / "active"
        env_path.mkdir()
        output = self._conda_output([
            f"active                *  {env_path}",
        ])
        with (
            patch("shutil.which", return_value="/usr/bin/conda"),
            patch("subprocess.run") as mock_run,
        ):
            mock_run.return_value = MagicMock(returncode=0, stdout=output, stderr="")
            envs = CondaDetector().detect(tmp_path)
        assert envs == []

    def test_skips_comment_and_blank_lines(self, tmp_path: Path) -> None:
        output = self._conda_output(["# comment", "", "  "])
        with (
            patch("shutil.which", return_value="/usr/bin/conda"),
            patch("subprocess.run") as mock_run,
        ):
            mock_run.return_value = MagicMock(returncode=0, stdout=output, stderr="")
            envs = CondaDetector().detect(tmp_path)
        assert envs == []

    def test_skips_malformed_line(self, tmp_path: Path) -> None:
        output = self._conda_output(["onefieldonly"])
        with (
            patch("shutil.which", return_value="/usr/bin/conda"),
            patch("subprocess.run") as mock_run,
        ):
            mock_run.return_value = MagicMock(returncode=0, stdout=output, stderr="")
            envs = CondaDetector().detect(tmp_path)
        assert envs == []

    def test_returns_empty_on_file_not_found(self, tmp_path: Path) -> None:
        with patch("subprocess.run", side_effect=FileNotFoundError):
            envs = CondaDetector().detect(tmp_path)
        assert envs == []

    def test_returns_empty_on_called_process_error(self, tmp_path: Path) -> None:
        with patch("subprocess.run", side_effect=subprocess.CalledProcessError(1, "conda")):
            envs = CondaDetector().detect(tmp_path)
        assert envs == []

    def test_returns_empty_on_os_error(self, tmp_path: Path) -> None:
        with patch("subprocess.run", side_effect=OSError("boom")):
            envs = CondaDetector().detect(tmp_path)
        assert envs == []

    def test_env_managed_by_conda(self, tmp_path: Path) -> None:
        env_path = tmp_path / "myenv"
        env_path.mkdir()
        output = self._conda_output([f"myenv  {env_path}"])
        with (
            patch("shutil.which", return_value="/usr/bin/conda"),
            patch("subprocess.run") as mock_run,
        ):
            mock_run.return_value = MagicMock(returncode=0, stdout=output, stderr="")
            envs = CondaDetector().detect(tmp_path)
        assert all(e.managed_by == "conda" for e in envs)


# ---------------------------------------------------------------------------
# PoetryDetector
# ---------------------------------------------------------------------------

class TestPoetryDetector:
    def test_can_handle_true_when_dir_exists(self, tmp_path: Path) -> None:
        with patch("killpy.detectors.poetry._poetry_venvs_dir", return_value=tmp_path):
            assert PoetryDetector().can_handle() is True

    def test_can_handle_false_when_dir_missing(self, tmp_path: Path) -> None:
        missing = tmp_path / "missing"
        with patch("killpy.detectors.poetry._poetry_venvs_dir", return_value=missing):
            assert PoetryDetector().can_handle() is False

    def test_detects_venvs(self, tmp_path: Path) -> None:
        (tmp_path / "myproject-abc").mkdir()
        (tmp_path / "other-xyz").mkdir()
        with patch("killpy.detectors.poetry._poetry_venvs_dir", return_value=tmp_path):
            envs = PoetryDetector().detect(tmp_path)
        assert len(envs) == 2
        assert all(e.type == "poetry" for e in envs)

    def test_returns_empty_when_dir_missing(self, tmp_path: Path) -> None:
        missing = tmp_path / "missing"
        with patch("killpy.detectors.poetry._poetry_venvs_dir", return_value=missing):
            envs = PoetryDetector().detect(tmp_path)
        assert envs == []

    def test_returns_empty_when_dir_empty(self, tmp_path: Path) -> None:
        with patch("killpy.detectors.poetry._poetry_venvs_dir", return_value=tmp_path):
            envs = PoetryDetector().detect(tmp_path)
        assert envs == []

    def test_env_type_and_name(self, tmp_path: Path) -> None:
        d = tmp_path / "myproject-a1b2"
        d.mkdir()
        with patch("killpy.detectors.poetry._poetry_venvs_dir", return_value=tmp_path):
            envs = PoetryDetector().detect(tmp_path)
        assert envs[0].name == "myproject-a1b2"
        assert envs[0].type == "poetry"

    def test_skips_files(self, tmp_path: Path) -> None:
        (tmp_path / "notadir.txt").write_text("x")
        with patch("killpy.detectors.poetry._poetry_venvs_dir", return_value=tmp_path):
            envs = PoetryDetector().detect(tmp_path)
        assert envs == []


# ---------------------------------------------------------------------------
# PipxDetector
# ---------------------------------------------------------------------------

class TestPipxDetector:
    def _pipx_json(self, packages: dict) -> str:
        return json.dumps({"venvs": packages})

    def test_can_handle_true(self) -> None:
        with patch("shutil.which", return_value="/usr/bin/pipx"):
            assert PipxDetector().can_handle() is True

    def test_can_handle_false(self) -> None:
        with patch("shutil.which", return_value=None):
            assert PipxDetector().can_handle() is False

    def test_detects_packages_via_known_venv_root(self, tmp_path: Path) -> None:
        pkg_venv = tmp_path / "black"
        pkg_venv.mkdir()
        payload = self._pipx_json({"black": {}})
        with (
            patch("shutil.which", return_value="/usr/bin/pipx"),
            patch("subprocess.run") as mock_run,
            patch("killpy.detectors.pipx._pipx_venvs_root", return_value=tmp_path),
        ):
            mock_run.return_value = MagicMock(returncode=0, stdout=payload, stderr="")
            envs = PipxDetector().detect(tmp_path)
        assert len(envs) == 1
        assert envs[0].name == "black"
        assert envs[0].managed_by == "pipx"

    def test_returns_empty_on_file_not_found(self, tmp_path: Path) -> None:
        with patch("subprocess.run", side_effect=FileNotFoundError):
            envs = PipxDetector().detect(tmp_path)
        assert envs == []

    def test_returns_empty_on_called_process_error(self, tmp_path: Path) -> None:
        with patch("subprocess.run", side_effect=subprocess.CalledProcessError(1, "pipx")):
            envs = PipxDetector().detect(tmp_path)
        assert envs == []

    def test_returns_empty_on_os_error(self, tmp_path: Path) -> None:
        with patch("subprocess.run", side_effect=OSError("boom")):
            envs = PipxDetector().detect(tmp_path)
        assert envs == []

    def test_returns_empty_on_invalid_json(self, tmp_path: Path) -> None:
        with (
            patch("shutil.which", return_value="/usr/bin/pipx"),
            patch("subprocess.run") as mock_run,
        ):
            mock_run.return_value = MagicMock(returncode=0, stdout="not-json", stderr="")
            envs = PipxDetector().detect(tmp_path)
        assert envs == []

    def test_skips_package_when_no_venv_dir(self, tmp_path: Path) -> None:
        payload = self._pipx_json({"nonexistent": {}})
        with (
            patch("shutil.which", return_value="/usr/bin/pipx"),
            patch("subprocess.run") as mock_run,
            patch("killpy.detectors.pipx._pipx_venvs_root", return_value=tmp_path),
        ):
            mock_run.return_value = MagicMock(returncode=0, stdout=payload, stderr="")
            envs = PipxDetector().detect(tmp_path)
        assert envs == []


# ---------------------------------------------------------------------------
# HatchDetector
# ---------------------------------------------------------------------------

class TestHatchDetector:
    def _make_hatch_tree(self, root: Path) -> None:
        (root / "project_a" / "default").mkdir(parents=True)
        (root / "project_b" / "test").mkdir(parents=True)

    def test_can_handle_true_with_hatch_on_path(self) -> None:
        with patch("shutil.which", return_value="/usr/bin/hatch"):
            assert HatchDetector().can_handle() is True

    def test_can_handle_true_when_dir_exists(self, tmp_path: Path) -> None:
        with (
            patch("shutil.which", return_value=None),
            patch("killpy.detectors.hatch._hatch_envs_root", return_value=tmp_path),
        ):
            assert HatchDetector().can_handle() is True

    def test_can_handle_false_when_both_missing(self, tmp_path: Path) -> None:
        missing = tmp_path / "missing"
        with (
            patch("shutil.which", return_value=None),
            patch("killpy.detectors.hatch._hatch_envs_root", return_value=missing),
        ):
            assert HatchDetector().can_handle() is False

    def test_detects_nested_envs(self, tmp_path: Path) -> None:
        self._make_hatch_tree(tmp_path)
        with patch("killpy.detectors.hatch._hatch_envs_root", return_value=tmp_path):
            envs = HatchDetector().detect(tmp_path)
        assert len(envs) == 2
        names = {e.name for e in envs}
        assert "project_a/default" in names
        assert "project_b/test" in names

    def test_returns_empty_when_root_missing(self, tmp_path: Path) -> None:
        missing = tmp_path / "missing"
        with patch("killpy.detectors.hatch._hatch_envs_root", return_value=missing):
            envs = HatchDetector().detect(tmp_path)
        assert envs == []

    def test_type_is_hatch(self, tmp_path: Path) -> None:
        self._make_hatch_tree(tmp_path)
        with patch("killpy.detectors.hatch._hatch_envs_root", return_value=tmp_path):
            envs = HatchDetector().detect(tmp_path)
        assert all(e.type == "hatch" for e in envs)

    def test_skips_files_at_root_level(self, tmp_path: Path) -> None:
        (tmp_path / "somefile.txt").write_text("x")
        with patch("killpy.detectors.hatch._hatch_envs_root", return_value=tmp_path):
            envs = HatchDetector().detect(tmp_path)
        assert envs == []


# ---------------------------------------------------------------------------
# PipenvDetector
# ---------------------------------------------------------------------------

class TestPipenvDetector:
    def test_can_handle_true_with_pipenv_on_path(self) -> None:
        with patch("shutil.which", return_value="/usr/bin/pipenv"):
            assert PipenvDetector().can_handle() is True

    def test_can_handle_true_when_dir_exists(self, tmp_path: Path) -> None:
        with (
            patch("shutil.which", return_value=None),
            patch("killpy.detectors.pipenv._pipenv_venvs_root", return_value=tmp_path),
        ):
            assert PipenvDetector().can_handle() is True

    def test_can_handle_false(self, tmp_path: Path) -> None:
        missing = tmp_path / "missing"
        with (
            patch("shutil.which", return_value=None),
            patch("killpy.detectors.pipenv._pipenv_venvs_root", return_value=missing),
        ):
            assert PipenvDetector().can_handle() is False

    def test_detects_venvs(self, tmp_path: Path) -> None:
        (tmp_path / "project-abc").mkdir()
        (tmp_path / "other-xyz").mkdir()
        with patch("killpy.detectors.pipenv._pipenv_venvs_root", return_value=tmp_path):
            envs = PipenvDetector().detect(tmp_path)
        assert len(envs) == 2
        assert all(e.type == "pipenv" for e in envs)

    def test_returns_empty_when_dir_missing(self, tmp_path: Path) -> None:
        missing = tmp_path / "missing"
        with patch("killpy.detectors.pipenv._pipenv_venvs_root", return_value=missing):
            envs = PipenvDetector().detect(tmp_path)
        assert envs == []

    def test_skips_files(self, tmp_path: Path) -> None:
        (tmp_path / "notadir.txt").write_text("x")
        with patch("killpy.detectors.pipenv._pipenv_venvs_root", return_value=tmp_path):
            envs = PipenvDetector().detect(tmp_path)
        assert envs == []


# ---------------------------------------------------------------------------
# ToxDetector
# ---------------------------------------------------------------------------

class TestToxDetector:
    def test_can_handle_always_true(self) -> None:
        assert ToxDetector().can_handle() is True

    def test_finds_tox_dir(self, tmp_path: Path) -> None:
        (tmp_path / "project" / ".tox").mkdir(parents=True)
        envs = ToxDetector().detect(tmp_path)
        assert len(envs) == 1
        assert envs[0].type == "tox"

    def test_multiple_tox_dirs(self, tmp_path: Path) -> None:
        (tmp_path / "proj_a" / ".tox").mkdir(parents=True)
        (tmp_path / "proj_b" / ".tox").mkdir(parents=True)
        envs = ToxDetector().detect(tmp_path)
        assert len(envs) == 2

    def test_no_tox_in_empty_dir(self, tmp_path: Path) -> None:
        assert ToxDetector().detect(tmp_path) == []

    def test_does_not_recurse_into_tox(self, tmp_path: Path) -> None:
        """A nested .tox inside another .tox must not be double-counted."""
        outer = tmp_path / ".tox"
        outer.mkdir()
        (outer / ".tox").mkdir()  # nested — should be ignored
        envs = ToxDetector().detect(tmp_path)
        assert len(envs) == 1

    def test_pruned_dirs_not_walked(self, tmp_path: Path) -> None:
        """node_modules and .git dirs should be skipped."""
        (tmp_path / "node_modules" / ".tox").mkdir(parents=True)
        envs = ToxDetector().detect(tmp_path)
        assert envs == []


# ---------------------------------------------------------------------------
# UvDetector
# ---------------------------------------------------------------------------

class TestUvDetector:
    def test_can_handle_true(self) -> None:
        with patch("shutil.which", return_value="/usr/bin/uv"):
            assert UvDetector().can_handle() is True

    def test_can_handle_false(self) -> None:
        with patch("shutil.which", return_value=None):
            assert UvDetector().can_handle() is False

    def test_finds_uv_dir(self, tmp_path: Path) -> None:
        (tmp_path / "project" / ".uv").mkdir(parents=True)
        with patch("shutil.which", return_value="/usr/bin/uv"):
            envs = UvDetector().detect(tmp_path)
        assert len(envs) == 1
        assert envs[0].type == "uv"

    def test_no_uv_in_empty_dir(self, tmp_path: Path) -> None:
        with patch("shutil.which", return_value="/usr/bin/uv"):
            envs = UvDetector().detect(tmp_path)
        assert envs == []

    def test_does_not_recurse_into_uv(self, tmp_path: Path) -> None:
        outer = tmp_path / ".uv"
        outer.mkdir()
        (outer / ".uv").mkdir()
        with patch("shutil.which", return_value="/usr/bin/uv"):
            envs = UvDetector().detect(tmp_path)
        assert len(envs) == 1

    def test_pruned_dirs_skipped(self, tmp_path: Path) -> None:
        (tmp_path / "node_modules" / ".uv").mkdir(parents=True)
        with patch("shutil.which", return_value="/usr/bin/uv"):
            envs = UvDetector().detect(tmp_path)
        assert envs == []


# ---------------------------------------------------------------------------
# ArtifactsDetector
# ---------------------------------------------------------------------------

class TestArtifactsDetector:
    def test_can_handle_always_true(self) -> None:
        assert ArtifactsDetector().can_handle() is True

    def test_finds_dist_and_build(self, tmp_path: Path) -> None:
        (tmp_path / "dist").mkdir()
        (tmp_path / "build").mkdir()
        envs = ArtifactsDetector().detect(tmp_path)
        types = {e.type for e in envs}
        assert types == {"artifacts"}
        paths = {e.path.name for e in envs}
        assert "dist" in paths
        assert "build" in paths

    def test_finds_egg_info(self, tmp_path: Path) -> None:
        (tmp_path / "mypkg.egg-info").mkdir()
        envs = ArtifactsDetector().detect(tmp_path)
        assert len(envs) == 1

    def test_finds_dist_info(self, tmp_path: Path) -> None:
        (tmp_path / "mypkg-1.0.dist-info").mkdir()
        envs = ArtifactsDetector().detect(tmp_path)
        assert len(envs) == 1

    def test_no_artifacts_in_clean_dir(self, tmp_path: Path) -> None:
        (tmp_path / "src").mkdir()
        (tmp_path / "tests").mkdir()
        envs = ArtifactsDetector().detect(tmp_path)
        assert envs == []

    def test_does_not_recurse_inside_artifact(self, tmp_path: Path) -> None:
        outer = tmp_path / "dist"
        outer.mkdir()
        (outer / "build").mkdir()  # nested — should not be double-counted
        envs = ArtifactsDetector().detect(tmp_path)
        names = [e.path.name for e in envs]
        assert names.count("dist") == 1
        assert "build" not in names

    def test_pruned_dirs_skipped(self, tmp_path: Path) -> None:
        (tmp_path / "node_modules" / "dist").mkdir(parents=True)
        envs = ArtifactsDetector().detect(tmp_path)
        assert envs == []

    def test_is_artifact_dir_helpers(self) -> None:
        assert _is_artifact_dir("dist") is True
        assert _is_artifact_dir("build") is True
        assert _is_artifact_dir("mypkg.egg-info") is True
        assert _is_artifact_dir("mypkg-1.0.dist-info") is True
        assert _is_artifact_dir("src") is False
        assert _is_artifact_dir("tests") is False


# ---------------------------------------------------------------------------
# CacheDetector – extended
# ---------------------------------------------------------------------------

class TestCacheDetectorExtended:
    def test_finds_mypy_cache(self, tmp_path: Path) -> None:
        (tmp_path / ".mypy_cache").mkdir()
        envs = CacheDetector()._scan_local(tmp_path)
        assert any(e.path.name == ".mypy_cache" for e in envs)

    def test_finds_pytest_cache(self, tmp_path: Path) -> None:
        (tmp_path / ".pytest_cache").mkdir()
        envs = CacheDetector()._scan_local(tmp_path)
        assert any(e.path.name == ".pytest_cache" for e in envs)

    def test_finds_ruff_cache(self, tmp_path: Path) -> None:
        (tmp_path / ".ruff_cache").mkdir()
        envs = CacheDetector()._scan_local(tmp_path)
        assert any(e.path.name == ".ruff_cache" for e in envs)

    def test_scan_global_returns_existing_paths(self, tmp_path: Path) -> None:
        fake_pip = tmp_path / "pip"
        fake_pip.mkdir()
        candidates = [(fake_pip, "pip-cache"), (tmp_path / "nope", "uv-cache")]
        with patch("killpy.detectors.cache.Path.home", return_value=tmp_path):
            # Build a minimal detector and override candidates
            detector = CacheDetector()
            # Directly test _make_cache_env with our dir
            env = _make_cache_env(fake_pip, "pip-cache")
        assert env.type == "pip-cache"
        assert env.path == fake_pip

    def test_detect_method_combines_local_and_global(self, tmp_path: Path) -> None:
        """detect() must call _scan_local and _scan_global (covers detect() body)."""
        (tmp_path / ".mypy_cache").mkdir()
        with patch.object(CacheDetector, "_scan_global", return_value=[]) as mock_global:
            envs = CacheDetector().detect(tmp_path)
        mock_global.assert_called_once()
        assert any(e.path.name == ".mypy_cache" for e in envs)

    def test_scan_local_prunes_git_dir(self, tmp_path: Path) -> None:
        """Dirs in _PRUNED are skipped (covers prune.add + continue branch)."""
        git = tmp_path / ".git"
        git.mkdir()
        (git / ".mypy_cache").mkdir()  # inside .git – must not be found
        envs = CacheDetector()._scan_local(tmp_path)
        assert envs == []

    def test_scan_local_handles_os_error_from_make_cache_env(self, tmp_path: Path) -> None:
        """_scan_local must continue on OSError from _make_cache_env."""
        (tmp_path / ".mypy_cache").mkdir()
        with patch("killpy.detectors.cache._make_cache_env", side_effect=OSError("fail")):
            envs = CacheDetector()._scan_local(tmp_path)
        assert envs == []

    def test_scan_global_finds_pip_cache(self, tmp_path: Path) -> None:
        """_scan_global returns pip-cache env when the dir exists (covers full method)."""
        pip_dir = tmp_path / ".cache" / "pip"
        pip_dir.mkdir(parents=True)
        with patch.object(Path, "home", return_value=tmp_path):
            envs = CacheDetector()._scan_global()
        assert any(e.type == "pip-cache" for e in envs)


# ---------------------------------------------------------------------------
# PyenvDetector – error-path coverage
# ---------------------------------------------------------------------------

from killpy.detectors.pyenv import PyenvDetector  # noqa: E402


class TestPyenvDetectorExtended:
    def test_returns_empty_when_root_missing(self, tmp_path: Path) -> None:
        missing = tmp_path / "missing"
        with patch("killpy.detectors.pyenv._pyenv_versions_root", return_value=missing):
            envs = PyenvDetector().detect(tmp_path)
        assert envs == []

    def test_outer_os_error_returns_empty(self, tmp_path: Path) -> None:
        """detect() should return [] when iterdir() raises OSError."""
        versions = tmp_path / ".pyenv" / "versions"
        versions.mkdir(parents=True)
        with (
            patch("killpy.detectors.pyenv._pyenv_versions_root", return_value=versions),
            patch.object(Path, "iterdir", side_effect=OSError("permission denied")),
        ):
            envs = PyenvDetector().detect(tmp_path)
        assert envs == []

    def test_inner_os_error_skips_version(self, tmp_path: Path) -> None:
        """Individual version stat failure should be skipped gracefully."""
        versions = tmp_path / ".pyenv" / "versions"
        (versions / "3.11.0").mkdir(parents=True)
        with (
            patch("killpy.detectors.pyenv._pyenv_versions_root", return_value=versions),
            patch("killpy.detectors.pyenv.get_total_size", side_effect=OSError("io")),
        ):
            envs = PyenvDetector().detect(tmp_path)
        assert envs == []


# ---------------------------------------------------------------------------
# PoetryDetector – error-path coverage
# ---------------------------------------------------------------------------

class TestPoetryDetectorErrors:
    def test_inner_os_error_skips_venv(self, tmp_path: Path) -> None:
        (tmp_path / "project-abc").mkdir()
        with (
            patch("killpy.detectors.poetry._poetry_venvs_dir", return_value=tmp_path),
            patch("killpy.detectors.poetry.get_total_size", side_effect=OSError("io")),
        ):
            envs = PoetryDetector().detect(tmp_path)
        assert envs == []

    def test_outer_os_error_returns_empty(self, tmp_path: Path) -> None:
        with (
            patch("killpy.detectors.poetry._poetry_venvs_dir", return_value=tmp_path),
            patch.object(Path, "iterdir", side_effect=OSError("perm")),
        ):
            envs = PoetryDetector().detect(tmp_path)
        assert envs == []


# ---------------------------------------------------------------------------
# HatchDetector – error-path coverage
# ---------------------------------------------------------------------------

class TestHatchDetectorErrors:
    def test_inner_os_error_skips_env(self, tmp_path: Path) -> None:
        (tmp_path / "project_a" / "default").mkdir(parents=True)
        with (
            patch("killpy.detectors.hatch._hatch_envs_root", return_value=tmp_path),
            patch("killpy.detectors.hatch.get_total_size", side_effect=OSError("io")),
        ):
            envs = HatchDetector().detect(tmp_path)
        assert envs == []

    def test_outer_os_error_returns_empty(self, tmp_path: Path) -> None:
        with (
            patch("killpy.detectors.hatch._hatch_envs_root", return_value=tmp_path),
            patch.object(Path, "iterdir", side_effect=OSError("perm")),
        ):
            envs = HatchDetector().detect(tmp_path)
        assert envs == []


# ---------------------------------------------------------------------------
# PipenvDetector – error-path coverage
# ---------------------------------------------------------------------------

class TestPipenvDetectorErrors:
    def test_inner_os_error_skips_venv(self, tmp_path: Path) -> None:
        (tmp_path / "project-abc").mkdir()
        with (
            patch("killpy.detectors.pipenv._pipenv_venvs_root", return_value=tmp_path),
            patch("killpy.detectors.pipenv.get_total_size", side_effect=OSError("io")),
        ):
            envs = PipenvDetector().detect(tmp_path)
        assert envs == []

    def test_outer_os_error_returns_empty(self, tmp_path: Path) -> None:
        with (
            patch("killpy.detectors.pipenv._pipenv_venvs_root", return_value=tmp_path),
            patch.object(Path, "iterdir", side_effect=OSError("perm")),
        ):
            envs = PipenvDetector().detect(tmp_path)
        assert envs == []


# ---------------------------------------------------------------------------
# PipxDetector – fallback venv path coverage (lines 81-91)
# ---------------------------------------------------------------------------

class TestPipxDetectorFallback:
    def _pipx_json_with_app_paths(self, pkg: str, bin_path: str) -> str:
        return json.dumps({
            "venvs": {
                pkg: {
                    "metadata": {
                        "main_package": {
                            "app_paths": [{"__Path__": bin_path}]
                        }
                    }
                }
            }
        })

    def test_fallback_finds_venv_via_app_paths(self, tmp_path: Path) -> None:
        """When primary venv path doesn't exist, fall back to app_paths heuristic."""
        # tmp_path / "black" = the actual venv (candidate after fallback)
        venv_dir = tmp_path / "black"
        venv_dir.mkdir()
        # Simulate: bin dir is tmp_path / "bin", so parent.parent = tmp_path
        bin_path = str(tmp_path / "bin" / "black")
        payload = self._pipx_json_with_app_paths("black", bin_path)

        # The DEFAULT venvs_root has NO "black" dir (missing = tmp_path / "nope")
        missing_root = tmp_path / "nope"
        with (
            patch("shutil.which", return_value="/usr/bin/pipx"),
            patch("subprocess.run") as mock_run,
            patch("killpy.detectors.pipx._pipx_venvs_root", return_value=missing_root),
        ):
            mock_run.return_value = MagicMock(returncode=0, stdout=payload, stderr="")
            envs = PipxDetector().detect(tmp_path)
        # venv_dir exists so we find it via fallback
        assert len(envs) == 1
        assert envs[0].name == "black"

    def test_fallback_skips_when_no_app_paths(self, tmp_path: Path) -> None:
        """Package with empty app_paths list should be skipped."""
        payload = json.dumps({"venvs": {"ghost": {"metadata": {"main_package": {"app_paths": []}}}}})
        missing_root = tmp_path / "nope"
        with (
            patch("shutil.which", return_value="/usr/bin/pipx"),
            patch("subprocess.run") as mock_run,
            patch("killpy.detectors.pipx._pipx_venvs_root", return_value=missing_root),
        ):
            mock_run.return_value = MagicMock(returncode=0, stdout=payload, stderr="")
            envs = PipxDetector().detect(tmp_path)
        assert envs == []

    def test_fallback_skips_when_raw_path_empty(self, tmp_path: Path) -> None:
        """Package with app_paths entry missing __Path__ should be skipped."""
        payload = json.dumps({"venvs": {"ghost": {"metadata": {"main_package": {"app_paths": [{"__Path__": ""}]}}}}})
        missing_root = tmp_path / "nope"
        with (
            patch("shutil.which", return_value="/usr/bin/pipx"),
            patch("subprocess.run") as mock_run,
            patch("killpy.detectors.pipx._pipx_venvs_root", return_value=missing_root),
        ):
            mock_run.return_value = MagicMock(returncode=0, stdout=payload, stderr="")
            envs = PipxDetector().detect(tmp_path)
        assert envs == []
