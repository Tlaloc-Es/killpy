"""Unit tests for ``killpy.intelligence.git_analyzer``."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

from killpy.intelligence.git_analyzer import GitAnalyzer


class TestFindRepoRoot:
    def test_finds_git_dir_in_current_folder(self, tmp_path: Path) -> None:
        (tmp_path / ".git").mkdir()
        assert GitAnalyzer.find_repo_root(tmp_path) == tmp_path

    def test_finds_git_dir_in_parent(self, tmp_path: Path) -> None:
        (tmp_path / ".git").mkdir()
        child = tmp_path / "sub" / "venv"
        child.mkdir(parents=True)
        assert GitAnalyzer.find_repo_root(child) == tmp_path

    def test_returns_none_when_no_git(self, tmp_path: Path) -> None:
        assert GitAnalyzer.find_repo_root(tmp_path) is None

    def test_returns_none_for_nonexistent_path(self) -> None:
        assert GitAnalyzer.find_repo_root(Path("/this/does/not/exist")) is None


class TestIsGitRepo:
    def test_true_for_git_repo(self, tmp_path: Path) -> None:
        (tmp_path / ".git").mkdir()
        assert GitAnalyzer.is_git_repo(tmp_path) is True

    def test_false_for_plain_dir(self, tmp_path: Path) -> None:
        assert GitAnalyzer.is_git_repo(tmp_path) is False


class TestGetLastCommit:
    def test_parses_unix_timestamp(self, tmp_path: Path) -> None:
        (tmp_path / ".git").mkdir()
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="1700000000\n")
            result = GitAnalyzer.get_last_commit(tmp_path)
        assert isinstance(result, datetime)
        assert result.tzinfo == timezone.utc
        assert result.year == 2023

    def test_returns_none_on_non_zero_exit(self, tmp_path: Path) -> None:
        (tmp_path / ".git").mkdir()
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=1, stdout="")
            result = GitAnalyzer.get_last_commit(tmp_path)
        assert result is None

    def test_returns_none_on_exception(self, tmp_path: Path) -> None:
        (tmp_path / ".git").mkdir()
        with patch("subprocess.run", side_effect=FileNotFoundError):
            result = GitAnalyzer.get_last_commit(tmp_path)
        assert result is None

    def test_returns_none_on_invalid_output(self, tmp_path: Path) -> None:
        (tmp_path / ".git").mkdir()
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="not-a-timestamp\n")
            result = GitAnalyzer.get_last_commit(tmp_path)
        assert result is None


class TestIsActiveRepo:
    def test_active_when_recent_commit(self, tmp_path: Path) -> None:
        recent = datetime.now(tz=timezone.utc)
        with patch.object(GitAnalyzer, "get_last_commit", return_value=recent):
            assert GitAnalyzer.is_active_repo(tmp_path, threshold_days=60) is True

    def test_inactive_when_old_commit(self, tmp_path: Path) -> None:
        old = datetime(2000, 1, 1, tzinfo=timezone.utc)
        with patch.object(GitAnalyzer, "get_last_commit", return_value=old):
            assert GitAnalyzer.is_active_repo(tmp_path, threshold_days=60) is False

    def test_inactive_when_no_commit(self, tmp_path: Path) -> None:
        with patch.object(GitAnalyzer, "get_last_commit", return_value=None):
            assert GitAnalyzer.is_active_repo(tmp_path, threshold_days=60) is False


class TestAnalyze:
    def test_returns_no_git_when_git_binary_missing(self, tmp_path: Path) -> None:
        with patch("shutil.which", return_value=None):
            result = GitAnalyzer.analyze(tmp_path)
        assert result.is_git_repo is False
        assert result.is_active is False

    def test_returns_git_info_for_active_repo(self, tmp_path: Path) -> None:
        (tmp_path / ".git").mkdir()
        recent = datetime.now(tz=timezone.utc)
        with (
            patch("shutil.which", return_value="/usr/bin/git"),
            patch.object(GitAnalyzer, "get_last_commit", return_value=recent),
        ):
            result = GitAnalyzer.analyze(tmp_path)
        assert result.is_git_repo is True
        assert result.is_active is True
        assert result.repo_root == tmp_path

    def test_returns_git_info_for_inactive_repo(self, tmp_path: Path) -> None:
        (tmp_path / ".git").mkdir()
        old = datetime(2000, 1, 1, tzinfo=timezone.utc)
        with (
            patch("shutil.which", return_value="/usr/bin/git"),
            patch.object(GitAnalyzer, "get_last_commit", return_value=old),
        ):
            result = GitAnalyzer.analyze(tmp_path)
        assert result.is_git_repo is True
        assert result.is_active is False
