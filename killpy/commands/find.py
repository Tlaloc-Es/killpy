"""``killpy find`` – locate environments that have a specific package installed."""

from __future__ import annotations

import json
from pathlib import Path

import click
from packaging.requirements import Requirement
from packaging.version import InvalidVersion
from rich.console import Console
from rich.table import Table

from killpy.commands._utils import filter_envs
from killpy.scanner import Scanner

# ---------------------------------------------------------------------------
# Helpers: read installed-package metadata from a venv directory
# ---------------------------------------------------------------------------


def _site_packages(env_path: Path) -> list[Path]:
    """Return all site-packages directories found inside *env_path*.

    Supports the Unix layout (``lib/python3.x/site-packages``) and the
    Windows layout (``Lib/site-packages``).
    """
    result: list[Path] = []

    # Unix: lib/python<ver>/site-packages
    lib = env_path / "lib"
    if lib.is_dir():
        for child in lib.iterdir():
            sp = child / "site-packages"
            if sp.is_dir():
                result.append(sp)

    # Windows: Lib/site-packages
    win_sp = env_path / "Lib" / "site-packages"
    if win_sp.is_dir():
        result.append(win_sp)

    return result


def _read_metadata_field(metadata_path: Path, field: str) -> str | None:
    """Return the value of a single RFC 822-style *field* from *metadata_path*."""
    prefix = f"{field}:"
    try:
        with metadata_path.open(encoding="utf-8", errors="replace") as fh:
            for line in fh:
                if line.startswith(prefix):
                    return line[len(prefix) :].strip()
                # RFC 822 headers end at the first blank line.
                if not line.strip():
                    break
    except OSError:
        pass
    return None


def _normalise_name(name: str) -> str:
    """Normalise a distribution name to a lowercase, underscore form."""
    return name.lower().replace("-", "_").replace(".", "_")


def installed_packages(env_path: Path) -> dict[str, str]:
    """Return ``{normalised_name: version}`` for every package installed in *env_path*.

    Reads ``*.dist-info/METADATA`` files from all site-packages directories
    found under the environment root.  Non-venv paths (e.g. conda envs created
    with ``--prefix``) are supported as long as they follow the same layout.
    """
    packages: dict[str, str] = {}
    for sp in _site_packages(env_path):
        for dist_info in sp.glob("*.dist-info"):
            metadata = dist_info / "METADATA"
            if not metadata.exists():
                continue
            name = _read_metadata_field(metadata, "Name")
            version = _read_metadata_field(metadata, "Version")
            if name and version:
                packages[_normalise_name(name)] = version
    return packages


def package_version_match(
    packages: dict[str, str], requirement: Requirement
) -> str | None:
    """Return the installed version string if it satisfies *requirement*, else ``None``."""  # noqa: E501
    norm_name = _normalise_name(requirement.name)
    installed = packages.get(norm_name)
    if installed is None:
        return None
    try:
        if requirement.specifier.contains(installed, prereleases=True):
            return installed
    except InvalidVersion:
        pass
    return None


# ---------------------------------------------------------------------------
# Click command
# ---------------------------------------------------------------------------


@click.command("find")
@click.argument("package")
@click.option(
    "--path",
    default=Path.cwd,
    type=click.Path(path_type=Path, exists=True, file_okay=False, dir_okay=True),
    help="Root directory to scan.",
)
@click.option(
    "--type",
    "types",
    multiple=True,
    metavar="TYPE",
    help=(
        "Limit the scan to these environment types (repeatable). "
        "Example: --type venv --type conda"
    ),
)
@click.option(
    "--json",
    "as_json",
    is_flag=True,
    default=False,
    help="Output as a JSON array.",
)
def find_cmd(
    package: str,
    path: Path,
    types: tuple[str, ...],
    as_json: bool,
) -> None:
    """Find environments that have PACKAGE installed.

    PACKAGE accepts standard PEP 508 / uv-style version specifiers:

    \b
        killpy find requests
        killpy find "requests>=2.28"
        killpy find "numpy>=1.24,<2.0"
        killpy find "django==4.2.*"
        killpy find "scipy~=1.11"
    """
    try:
        req = Requirement(package)
    except Exception as exc:  # packaging.requirements.InvalidRequirement
        raise click.BadParameter(str(exc), param_hint="PACKAGE") from exc

    scanner = Scanner(types=set(types) if types else None)
    envs = scanner.scan(path)
    envs = filter_envs(envs, types or None, None)

    matches: list[tuple] = []  # (Environment, version_string)
    for env in envs:
        pkgs = installed_packages(env.path)
        version = package_version_match(pkgs, req)
        if version is not None:
            matches.append((env, version))

    if as_json:
        click.echo(
            json.dumps(
                [{**env.to_dict(), "matched_version": ver} for env, ver in matches],
                indent=2,
            )
        )
        return

    console = Console()

    if not matches:
        console.print(
            f"[yellow]No environments found with[/yellow] "
            f"[bold]{package}[/bold] installed."
        )
        return

    table = Table(title=f"Environments with {package!r}", show_lines=False)
    table.add_column("Path", style="cyan")
    table.add_column("Type", style="magenta")
    table.add_column("Installed version", style="green")
    table.add_column("Env size", style="yellow", justify="right")

    for env, ver in matches:
        table.add_row(str(env.path), env.type, ver, env.size_human)

    console.print(table)
    console.print(
        f"\n[bold]{len(matches)}[/bold] environment(s) match "
        f"[bold cyan]{package}[/bold cyan]."
    )
