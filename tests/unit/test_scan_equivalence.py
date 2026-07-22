"""Golden equivalence test for the filesystem-walking detectors.

Locks the exact set of environments (path, type, recursive byte size) that
``venv`` / ``cache`` / ``artifacts`` / ``tox`` report on a realistic tree, so
the shared-filesystem-walk refactor (GIT-2) can be proven behaviour-preserving:
the new single-pass scanner must reproduce ``_GOLDEN`` byte-for-byte.

The fixture deliberately contains no environment nested inside another
environment's ``site-packages`` — the one case where the refactor's central
env-pruning is intentionally *not* byte-equivalent to the old per-detector
descent (see ``test_env_pruning_stops_at_venv_boundary``).
"""

from __future__ import annotations

from pathlib import Path

from killpy.scanner import Scanner

_FS_WALK_DETECTORS = {"venv", "cache", "artifacts", "tox"}
_BLOB = b"x" * 100  # every fixture file is exactly 100 bytes

# (path relative to scan root, Environment.type, size_bytes) — captured from the
# per-detector implementation and frozen. Any drift is a behaviour change.
_GOLDEN = [
    ("proj_a/.venv", ".venv", 500),
    ("proj_a/__pycache__", "__pycache__", 200),
    ("proj_a/build", "artifacts", 100),
    ("proj_a/dist", "artifacts", 100),
    ("proj_a/proj_a.egg-info", "artifacts", 100),
    ("proj_a/src/pkg/__pycache__", "__pycache__", 100),
    ("proj_b/.pytest_cache", ".pytest_cache", 100),
    ("proj_b/.tox", "tox", 100),
    ("proj_b/myenv", "pyvenv.cfg", 200),
    ("proj_c/.ruff_cache", ".ruff_cache", 100),
]


def _w(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(_BLOB)


def _build_tree(root: Path) -> None:
    """Create a deterministic tree exercising every fs-walking detector."""
    # proj_a — a real .venv with a populated site-packages, plus a top-level
    # cache, build artifacts, and a nested source __pycache__.
    a = root / "proj_a"
    _w(a / "pyproject.toml")
    _w(a / ".venv" / "pyvenv.cfg")
    _w(a / ".venv" / "lib" / "site-packages" / "pkg1" / "__init__.py")
    _w(a / ".venv" / "lib" / "site-packages" / "pkg1" / "mod.py")
    _w(a / ".venv" / "lib" / "site-packages" / "pkg1-1.0.dist-info" / "METADATA")
    _w(a / ".venv" / "lib" / "site-packages" / "pkg1-1.0.dist-info" / "RECORD")
    _w(a / "__pycache__" / "a.pyc")
    _w(a / "__pycache__" / "b.pyc")
    _w(a / "build" / "out.bin")
    _w(a / "dist" / "out.bin")
    _w(a / "proj_a.egg-info" / "PKG-INFO")
    _w(a / "src" / "pkg" / "__init__.py")
    _w(a / "src" / "pkg" / "__pycache__" / "m.pyc")

    # proj_b — a venv NOT named .venv (found via pyvenv.cfg) with a cache inside
    # it (must fold into the venv size, never be reported on its own), plus a
    # top-level .tox and a top-level cache.
    b = root / "proj_b"
    _w(b / "myenv" / "pyvenv.cfg")
    _w(b / "myenv" / ".mypy_cache" / "x.bin")
    _w(b / ".tox" / "py" / "lib" / "t.bin")
    _w(b / ".pytest_cache" / "v.bin")

    # proj_c — a lone ruff cache
    _w(root / "proj_c" / ".ruff_cache" / "r.bin")

    # a VCS dir that must be pruned everywhere (never reported, never counted)
    _w(root / ".git" / "config")


def _scan_rows(root: Path) -> list[tuple[str, str, int]]:
    envs = Scanner(types=_FS_WALK_DETECTORS).scan(root)
    return sorted((str(e.path.relative_to(root)), e.type, e.size_bytes) for e in envs)


def test_fs_walk_detectors_match_golden(tmp_path: Path) -> None:
    """The four fs-walking detectors report exactly the frozen golden set."""
    _build_tree(tmp_path)
    assert _scan_rows(tmp_path) == _GOLDEN


def test_cache_inside_venv_is_not_double_counted(tmp_path: Path) -> None:
    """A cache dir inside a venv folds into the venv size, unreported on its own."""
    _build_tree(tmp_path)
    rows = _scan_rows(tmp_path)
    # proj_b/myenv holds a .mypy_cache; it must not appear as its own env…
    assert not any(r[0] == "proj_b/myenv/.mypy_cache" for r in rows)
    # …and the venv size (pyvenv.cfg + the cache file) must be the full 200 B.
    assert ("proj_b/myenv", "pyvenv.cfg", 200) in rows
