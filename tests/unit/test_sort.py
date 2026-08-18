"""Unit tests for sort_envs helper and killpy list --sort / --reverse flags."""

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from click.testing import CliRunner

from killpy.__main__ import cli
from killpy.commands._utils import sort_envs
from killpy.models import Environment


def _make_env(name: str, size: int, days_old: int) -> Environment:
    now = datetime.now(tz=timezone.utc)
    return Environment(
        path=Path(f"/tmp/{name}"),
        name=name,
        type="venv",
        last_modified=now - timedelta(days=days_old),
        size_bytes=size,
    )


class TestSortEnvsHelper:
    def test_sort_by_size_default_descending(self) -> None:
        e1 = _make_env("small", 100, 10)
        e2 = _make_env("large", 1000, 5)
        e3 = _make_env("medium", 500, 1)

        result = sort_envs([e1, e2, e3], sort_by="size")
        assert [e.name for e in result] == ["large", "medium", "small"]

    def test_sort_by_size_reversed_ascending(self) -> None:
        e1 = _make_env("small", 100, 10)
        e2 = _make_env("large", 1000, 5)
        e3 = _make_env("medium", 500, 1)

        result = sort_envs([e1, e2, e3], sort_by="size", reverse=True)
        assert [e.name for e in result] == ["small", "medium", "large"]

    def test_sort_by_date_default_newest_first(self) -> None:
        e1 = _make_env("old", 100, 100)
        e2 = _make_env("newest", 100, 1)
        e3 = _make_env("medium", 100, 10)

        result = sort_envs([e1, e2, e3], sort_by="date")
        assert [e.name for e in result] == ["newest", "medium", "old"]

    def test_sort_by_date_reversed_oldest_first(self) -> None:
        e1 = _make_env("old", 100, 100)
        e2 = _make_env("newest", 100, 1)
        e3 = _make_env("medium", 100, 10)

        result = sort_envs([e1, e2, e3], sort_by="date", reverse=True)
        assert [e.name for e in result] == ["old", "medium", "newest"]

    def test_sort_by_name_default_alphabetical(self) -> None:
        e1 = _make_env("charlie", 100, 10)
        e2 = _make_env("alpha", 100, 10)
        e3 = _make_env("bravo", 100, 10)

        result = sort_envs([e1, e2, e3], sort_by="name")
        assert [e.name for e in result] == ["alpha", "bravo", "charlie"]

    def test_sort_by_name_reversed_reverse_alphabetical(self) -> None:
        e1 = _make_env("charlie", 100, 10)
        e2 = _make_env("alpha", 100, 10)
        e3 = _make_env("bravo", 100, 10)

        result = sort_envs([e1, e2, e3], sort_by="name", reverse=True)
        assert [e.name for e in result] == ["charlie", "bravo", "alpha"]

    def test_sort_by_name_case_insensitive(self) -> None:
        e1 = _make_env("Zulu", 100, 10)
        e2 = _make_env("alpha", 100, 10)

        result = sort_envs([e1, e2], sort_by="name")
        assert [e.name for e in result] == ["alpha", "Zulu"]

    def test_invalid_sort_key_raises_value_error(self) -> None:
        e1 = _make_env("test", 100, 10)
        with pytest.raises(ValueError, match="Invalid sort key"):
            sort_envs([e1], sort_by="invalid_key")


class TestListCommandSorting:
    def test_list_sort_size_json(self) -> None:
        envs = [
            _make_env("small", 100, 10),
            _make_env("large", 1000, 5),
            _make_env("medium", 500, 1),
        ]
        runner = CliRunner()
        with patch("killpy.commands.list.Scanner") as mock_scanner:
            mock_scanner.return_value.scan.return_value = envs
            result = runner.invoke(cli, ["list", "--json", "--sort", "size"])

        assert result.exit_code == 0
        names = [item["name"] for item in json.loads(result.output)]
        assert names == ["large", "medium", "small"]

    def test_list_sort_size_reverse_json(self) -> None:
        envs = [
            _make_env("small", 100, 10),
            _make_env("large", 1000, 5),
            _make_env("medium", 500, 1),
        ]
        runner = CliRunner()
        with patch("killpy.commands.list.Scanner") as mock_scanner:
            mock_scanner.return_value.scan.return_value = envs
            result = runner.invoke(
                cli, ["list", "--json", "--sort", "size", "--reverse"]
            )

        assert result.exit_code == 0
        names = [item["name"] for item in json.loads(result.output)]
        assert names == ["small", "medium", "large"]

    def test_list_sort_name_json(self) -> None:
        envs = [
            _make_env("charlie", 100, 10),
            _make_env("alpha", 1000, 5),
            _make_env("bravo", 500, 1),
        ]
        runner = CliRunner()
        with patch("killpy.commands.list.Scanner") as mock_scanner:
            mock_scanner.return_value.scan.return_value = envs
            result = runner.invoke(cli, ["list", "--json", "-s", "name"])

        assert result.exit_code == 0
        names = [item["name"] for item in json.loads(result.output)]
        assert names == ["alpha", "bravo", "charlie"]

    def test_list_sort_date_json(self) -> None:
        envs = [
            _make_env("old", 100, 100),
            _make_env("newest", 1000, 1),
            _make_env("medium", 500, 10),
        ]
        runner = CliRunner()
        with patch("killpy.commands.list.Scanner") as mock_scanner:
            mock_scanner.return_value.scan.return_value = envs
            result = runner.invoke(cli, ["list", "--json", "-s", "date"])

        assert result.exit_code == 0
        names = [item["name"] for item in json.loads(result.output)]
        assert names == ["newest", "medium", "old"]

    def test_list_sort_date_reverse_json(self) -> None:
        envs = [
            _make_env("old", 100, 100),
            _make_env("newest", 1000, 1),
            _make_env("medium", 500, 10),
        ]
        runner = CliRunner()
        with patch("killpy.commands.list.Scanner") as mock_scanner:
            mock_scanner.return_value.scan.return_value = envs
            result = runner.invoke(cli, ["list", "--json", "-s", "date", "-r"])

        assert result.exit_code == 0
        names = [item["name"] for item in json.loads(result.output)]
        assert names == ["old", "medium", "newest"]

    def test_list_json_stream_keeps_detection_order(self) -> None:
        """--sort must not reorder the stream: batches are emitted as detected,
        so a globally sorted stream is impossible without buffering the scan."""
        batch_small = [_make_env("small-venv", 100, 1)]
        batch_big = [_make_env("huge-artifact", 9000, 1)]

        def fake_scan(path, on_progress=None):
            on_progress(SimpleNamespace(name="venv"), batch_small)
            on_progress(SimpleNamespace(name="artifacts"), batch_big)
            return batch_small + batch_big

        runner = CliRunner()
        with patch("killpy.commands.list.Scanner") as mock_scanner:
            mock_scanner.return_value.scan.side_effect = fake_scan
            result = runner.invoke(
                cli, ["list", "--json-stream", "--sort", "size", "--quiet"]
            )

        assert result.exit_code == 0
        lines = result.output.strip().splitlines()
        names = [json.loads(line)["name"] for line in lines]
        assert names == ["small-venv", "huge-artifact"]
