"""System-level end-to-end tests: real environments, the real CLI, real deletion.

Unlike the unit suite (synthetic trees + mocks), these build a **genuine** venv
via ``ensurepip``, invoke the installed ``killpy`` CLI as a subprocess, and then
**actually delete** the environments — verifying that killpy removes exactly what
it should and leaves everything else intact.

Because they delete files for real, they are gated behind ``KILLPY_INTEGRATION=1``
and meant to run inside a disposable sandbox (the ``Dockerfile.integration`` image
or a throwaway CI runner), never on a developer machine's real tree::

    KILLPY_INTEGRATION=1 uv run pytest -m integration --no-cov tests/integration
    docker build -f Dockerfile.integration -t killpy-it . && docker run --rm killpy-it
"""

from __future__ import annotations

import json
import os
import py_compile
import subprocess
import sys
import venv
from pathlib import Path

import pytest

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        os.environ.get("KILLPY_INTEGRATION") != "1",
        reason="set KILLPY_INTEGRATION=1 to run these (disposable sandbox only)",
    ),
]

_VENV_TYPES = {".venv", "pyvenv.cfg"}
_CACHE_TYPES = {"__pycache__", ".mypy_cache", ".pytest_cache", ".ruff_cache"}


def _killpy(*args: str) -> subprocess.CompletedProcess[str]:
    """Invoke the real killpy CLI as a subprocess (same interpreter/env)."""
    return subprocess.run(
        [sys.executable, "-m", "killpy", *args],
        capture_output=True,
        text=True,
        check=False,
    )


def _list_json(root: Path) -> list[dict]:
    result = _killpy("list", "--path", str(root), "--json", "--quiet")
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)


@pytest.fixture
def real_tree(tmp_path: Path) -> Path:
    """A project with a REAL venv (ensurepip), plus real caches and artifacts."""
    proj = tmp_path / "app"
    (proj / "src").mkdir(parents=True)

    # A genuine virtualenv: real pyvenv.cfg + a site-packages populated by ensurepip.
    venv.create(proj / ".venv", with_pip=True)

    # A real __pycache__ produced by compiling a module.
    module = proj / "src" / "mod.py"
    module.write_text("VALUE = 1\n")
    py_compile.compile(str(module))

    # Real cache and build-artifact directories (detected by name).
    for name in (".mypy_cache", ".pytest_cache", ".ruff_cache"):
        cache = proj / name
        cache.mkdir()
        (cache / "CACHEDIR.TAG").write_text("Signature: killpy-test\n")
    for name in ("build", "dist"):
        artifact = proj / name
        artifact.mkdir()
        (artifact / "wheel.bin").write_bytes(b"x" * 4096)

    return tmp_path


def test_detects_real_environments(real_tree: Path) -> None:
    """`killpy list --json` finds the real venv, caches and artifacts."""
    envs = _list_json(real_tree)
    types = {e["type"] for e in envs}

    assert types & _VENV_TYPES, f"no venv detected in {types}"
    assert types & _CACHE_TYPES, f"no cache detected in {types}"
    assert "artifacts" in types, f"no artifacts detected in {types}"

    # A real venv is non-trivial in size (ensurepip installed packages).
    venv_env = next(e for e in envs if e["type"] in _VENV_TYPES)
    assert venv_env["size_bytes"] > 0


def test_delete_caches_leaves_venv_intact(real_tree: Path) -> None:
    """`delete --type cache --yes` removes caches but never touches the venv."""
    venv_dir = real_tree / "app" / ".venv"
    mypy_cache = real_tree / "app" / ".mypy_cache"
    assert venv_dir.exists() and mypy_cache.exists()

    result = _killpy("delete", "--path", str(real_tree), "--type", "cache", "--yes")
    assert result.returncode == 0, result.stderr

    assert not mypy_cache.exists(), "cache was not actually deleted"
    assert venv_dir.exists(), "venv must survive a cache-only delete"
    assert (venv_dir / "pyvenv.cfg").exists()


def test_delete_venv_removes_it(real_tree: Path) -> None:
    """`delete --type venv --yes` really removes the virtualenv from disk."""
    venv_dir = real_tree / "app" / ".venv"
    assert (venv_dir / "pyvenv.cfg").exists()

    result = _killpy("delete", "--path", str(real_tree), "--type", "venv", "--yes")
    assert result.returncode == 0, result.stderr

    assert not venv_dir.exists(), "venv was not actually deleted"
    # unrelated artifacts must remain
    assert (real_tree / "app" / "dist").exists()
