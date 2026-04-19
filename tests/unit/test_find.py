"""Unit tests for ``killpy find`` command and its metadata helpers."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

from click.testing import CliRunner
from packaging.requirements import Requirement

from killpy.__main__ import cli
from killpy.commands.find import (
    _normalise_name,
    _site_packages,
    installed_packages,
    package_version_match,
)
from killpy.models import Environment

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _env(path: Path | None = None, env_type: str = "venv") -> Environment:
    return Environment(
        path=path or Path("/fake/myenv"),
        name="myenv",
        type=env_type,
        last_accessed=datetime(2024, 3, 15, tzinfo=timezone.utc),
        size_bytes=1024,
    )


def _make_dist_info(sp: Path, name: str, version: str) -> None:
    """Create a minimal .dist-info directory with a METADATA file."""
    dist_info = sp / f"{name}-{version}.dist-info"
    dist_info.mkdir(parents=True)
    (dist_info / "METADATA").write_text(
        f"Metadata-Version: 2.1\nName: {name}\nVersion: {version}\n\nBody\n"
    )


# ---------------------------------------------------------------------------
# _normalise_name
# ---------------------------------------------------------------------------


class TestNormaliseName:
    def test_lowercase(self):
        assert _normalise_name("Requests") == "requests"

    def test_dashes_to_underscores(self):
        assert _normalise_name("my-package") == "my_package"

    def test_dots_to_underscores(self):
        assert _normalise_name("my.package") == "my_package"

    def test_combined(self):
        assert _normalise_name("My-Cool.Package") == "my_cool_package"


# ---------------------------------------------------------------------------
# _site_packages
# ---------------------------------------------------------------------------


class TestSitePackages:
    def test_unix_layout(self, tmp_path: Path):
        sp = tmp_path / "lib" / "python3.12" / "site-packages"
        sp.mkdir(parents=True)
        result = _site_packages(tmp_path)
        assert sp in result

    def test_windows_layout(self, tmp_path: Path):
        sp = tmp_path / "Lib" / "site-packages"
        sp.mkdir(parents=True)
        result = _site_packages(tmp_path)
        assert sp in result

    def test_empty_venv(self, tmp_path: Path):
        assert _site_packages(tmp_path) == []


# ---------------------------------------------------------------------------
# installed_packages
# ---------------------------------------------------------------------------


class TestInstalledPackages:
    def test_reads_metadata(self, tmp_path: Path):
        sp = tmp_path / "lib" / "python3.12" / "site-packages"
        sp.mkdir(parents=True)
        _make_dist_info(sp, "requests", "2.31.0")
        pkgs = installed_packages(tmp_path)
        assert pkgs["requests"] == "2.31.0"

    def test_normalises_hyphenated_names(self, tmp_path: Path):
        sp = tmp_path / "lib" / "python3.12" / "site-packages"
        sp.mkdir(parents=True)
        _make_dist_info(sp, "my-package", "1.0.0")
        pkgs = installed_packages(tmp_path)
        assert "my_package" in pkgs

    def test_missing_metadata_skipped(self, tmp_path: Path):
        sp = tmp_path / "lib" / "python3.12" / "site-packages"
        sp.mkdir(parents=True)
        # dist-info without METADATA
        (sp / "broken-1.0.dist-info").mkdir()
        pkgs = installed_packages(tmp_path)
        assert pkgs == {}

    def test_empty_env(self, tmp_path: Path):
        assert installed_packages(tmp_path) == {}


# ---------------------------------------------------------------------------
# package_version_match
# ---------------------------------------------------------------------------


class TestPackageVersionMatch:
    def _pkgs(self, **kwargs: str) -> dict[str, str]:
        return {_normalise_name(k): v for k, v in kwargs.items()}

    def test_no_specifier_matches_any_version(self):
        assert (
            package_version_match(
                self._pkgs(requests="2.31.0"), Requirement("requests")
            )
            == "2.31.0"
        )

    def test_exact_version_matches(self):
        assert (
            package_version_match(
                self._pkgs(requests="2.31.0"), Requirement("requests==2.31.0")
            )
            == "2.31.0"
        )

    def test_exact_version_no_match(self):
        assert (
            package_version_match(
                self._pkgs(requests="2.30.0"), Requirement("requests==2.31.0")
            )
            is None
        )

    def test_gte_specifier_matches(self):
        assert (
            package_version_match(
                self._pkgs(numpy="1.26.0"), Requirement("numpy>=1.24")
            )
            == "1.26.0"
        )

    def test_gte_specifier_no_match(self):
        assert (
            package_version_match(
                self._pkgs(numpy="1.23.0"), Requirement("numpy>=1.24")
            )
            is None
        )

    def test_range_specifier_matches(self):
        assert (
            package_version_match(
                self._pkgs(numpy="1.25.0"), Requirement("numpy>=1.24,<2.0")
            )
            == "1.25.0"
        )

    def test_range_specifier_upper_no_match(self):
        assert (
            package_version_match(
                self._pkgs(numpy="2.0.0"), Requirement("numpy>=1.24,<2.0")
            )
            is None
        )

    def test_tilde_equal_specifier(self):
        assert (
            package_version_match(
                self._pkgs(scipy="1.11.3"), Requirement("scipy~=1.11")
            )
            == "1.11.3"
        )

    def test_package_not_present(self):
        assert (
            package_version_match(self._pkgs(requests="2.31.0"), Requirement("flask"))
            is None
        )

    def test_wildcard_version(self):
        assert (
            package_version_match(
                self._pkgs(django="4.2.5"), Requirement("django==4.2.*")
            )
            == "4.2.5"
        )


# ---------------------------------------------------------------------------
# CLI: killpy find
# ---------------------------------------------------------------------------


class TestFindCommand:
    def _run(self, args: list[str], envs: list[Environment], pkgs: dict[str, str]):
        runner = CliRunner()
        mock_scanner = MagicMock()
        mock_scanner.return_value.scan.return_value = envs
        with (
            patch("killpy.commands.find.Scanner", mock_scanner),
            patch("killpy.commands.find.installed_packages", return_value=pkgs),
        ):
            return runner.invoke(cli, ["find"] + args, catch_exceptions=False)

    def test_found_table_output(self):
        env = _env(Path("/proj/.venv"))
        result = self._run(["requests>=2.0"], [env], {"requests": "2.31.0"})
        assert result.exit_code == 0
        assert "2.31.0" in result.output
        assert "/proj/.venv" in result.output

    def test_not_found_message(self):
        env = _env(Path("/proj/.venv"))
        result = self._run(["flask>=3.0"], [env], {"requests": "2.31.0"})
        assert result.exit_code == 0
        assert "No environments found" in result.output

    def test_json_output(self):
        env = _env(Path("/proj/.venv"))
        result = self._run(["requests", "--json"], [env], {"requests": "2.31.0"})
        assert result.exit_code == 0
        data = __import__("json").loads(result.output)
        assert len(data) == 1
        assert data[0]["matched_version"] == "2.31.0"

    def test_invalid_specifier(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["find", "requests>>>bad"], catch_exceptions=False)
        assert result.exit_code != 0

    def test_no_match_exits_cleanly(self):
        result = self._run(["numpy==99.0"], [], {})
        assert result.exit_code == 0
