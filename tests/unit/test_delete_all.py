"""Tests for ``killpy --delete-all`` (``killpy/__main__.py::_run_delete_all``).

Scanner and Cleaner are replaced with fakes: running the real ones would
scan — and delete — actual environments on the developer machine.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest

import killpy.__main__ as main_mod
from killpy.cleaner import CleanerError
from killpy.intelligence.tracker import UsageTracker
from killpy.models import Environment


def _make_env(path: str, size: int) -> Environment:
    return Environment(
        path=Path(path),
        name=path,
        type=".venv",
        last_accessed=datetime(2024, 1, 1, tzinfo=timezone.utc),
        size_bytes=size,
    )


def _patch_pipeline(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    envs: list[Environment],
    fail_paths: frozenset[Path] = frozenset(),
) -> list[Environment]:
    """Replace Scanner/Cleaner/UsageTracker in ``killpy.__main__``.

    Returns the list that collects successfully "deleted" environments.
    """
    deleted: list[Environment] = []

    class FakeScanner:
        def __init__(self, *args, **kwargs) -> None:
            pass

        def scan(self, path: Path) -> list[Environment]:
            return list(envs)

    class FakeCleaner:
        def __init__(self, *args, **kwargs) -> None:
            pass

        def delete(self, env: Environment) -> int:
            if env.path in fail_paths:
                raise CleanerError(f"cannot delete {env.path}")
            deleted.append(env)
            return env.size_bytes

    monkeypatch.setattr(main_mod, "Scanner", FakeScanner)
    monkeypatch.setattr(main_mod, "Cleaner", FakeCleaner)
    monkeypatch.setattr(
        main_mod,
        "UsageTracker",
        lambda: UsageTracker(storage_path=tmp_path / "history.json"),
    )
    return deleted


def test_delete_all_continues_after_a_failed_deletion(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """A CleanerError must not abort the loop; it is reported and counted.

    Regression test: the error used to propagate as an uncaught traceback,
    aborting the mass deletion halfway with no summary.
    """
    env_ok1 = _make_env("/data/a/.venv", 10)
    env_bad = _make_env("/data/b/.venv", 20)
    env_ok2 = _make_env("/data/c/.venv", 30)
    deleted = _patch_pipeline(
        monkeypatch,
        tmp_path,
        [env_ok1, env_bad, env_ok2],
        fail_paths=frozenset({env_bad.path}),
    )

    with pytest.raises(SystemExit) as excinfo:
        main_mod._run_delete_all(tmp_path, set(), yes=True)

    assert excinfo.value.code == 1
    assert deleted == [env_ok1, env_ok2]

    output = capsys.readouterr().out
    assert "Failed to delete" in output
    assert "Deleted 2/3" in output

    # The history record must be updated even when some deletions fail.
    summary = UsageTracker(storage_path=tmp_path / "history.json").get_summary()
    assert summary["total_space_deleted"] == 40


def test_delete_all_counts_zero_byte_env_as_deleted(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """An empty (0-byte) environment is a successful deletion, not a failure.

    Regression test: the return value of ``Cleaner.delete`` (bytes freed)
    was treated as a success flag, so 0-byte environments were reported
    as 'Failed to delete'.
    """
    env_empty = _make_env("/data/empty/.venv", 0)
    deleted = _patch_pipeline(monkeypatch, tmp_path, [env_empty])

    main_mod._run_delete_all(tmp_path, set(), yes=True)

    assert deleted == [env_empty]
    output = capsys.readouterr().out
    assert "Failed to delete" not in output
    assert "Deleted 1/1" in output


def test_delete_all_reports_when_nothing_found(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _patch_pipeline(monkeypatch, tmp_path, [])

    main_mod._run_delete_all(tmp_path, set(), yes=True)

    assert "No environments found" in capsys.readouterr().out
