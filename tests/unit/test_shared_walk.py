"""Unit tests for the single shared filesystem walk."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from killpy.detectors._shared_walk import walk_environments


def _make_tree(root: Path) -> None:
    proj = root / "proj"
    (proj / ".venv").mkdir(parents=True)
    (proj / ".venv" / "pyvenv.cfg").write_text("home = /usr/bin\n")
    (proj / ".venv" / "lib" / "site-packages").mkdir(parents=True)
    (proj / "__pycache__").mkdir()
    (proj / "build").mkdir()
    (proj / ".tox").mkdir()


def test_walk_reports_each_active_type(tmp_path: Path) -> None:
    _make_tree(tmp_path)
    envs = walk_environments(tmp_path, {"venv", "cache", "artifacts", "tox"})
    assert {e.type for e in envs} == {".venv", "__pycache__", "artifacts", "tox"}


def test_walk_active_subset_still_prunes_other_containers(tmp_path: Path) -> None:
    """Non-active containers are not reported but are still pruned (not descended)."""
    _make_tree(tmp_path)
    envs = walk_environments(tmp_path, {"tox"})
    assert {e.type for e in envs} == {"tox"}


def test_make_env_oserror_skips_container(tmp_path: Path) -> None:
    """If sizing a container raises OSError, it is skipped, not crashed on."""
    _make_tree(tmp_path)
    with patch(
        "killpy.detectors._shared_walk.get_total_size", side_effect=OSError("boom")
    ):
        envs = walk_environments(tmp_path, {"cache"})
    assert envs == []


def test_bare_site_packages_is_pruned(tmp_path: Path) -> None:
    """A conda-style ``site-packages`` (no pyvenv.cfg) is never scanned inside."""
    site = tmp_path / "envs" / "ml" / "lib" / "site-packages"
    (site / "mypkg-1.0.dist-info").mkdir(parents=True)
    assert walk_environments(tmp_path, {"artifacts"}) == []


def test_pyvenv_named_env_reported_as_pyvenv_cfg(tmp_path: Path) -> None:
    """A venv not called ``.venv`` is found via pyvenv.cfg and tagged accordingly."""
    env = tmp_path / "custom-env"
    env.mkdir()
    (env / "pyvenv.cfg").write_text("home = /usr/bin\n")
    envs = walk_environments(tmp_path, {"venv"})
    assert [e.type for e in envs] == ["pyvenv.cfg"]
