"""``killpy doctor`` – environment health report with smart suggestions."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import click
from rich.console import Console
from rich.table import Table

from killpy.detectors import ALL_DETECTORS
from killpy.files import format_size
from killpy.intelligence import SuggestionEngine, UsageTracker, score_all
from killpy.models import Suggestion
from killpy.scanner import Scanner

# Environments smaller than this threshold are excluded from "wasted" totals.
_IMPACTFUL_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB
_SMALL_SIZE_BYTES = 1 * 1024 * 1024  # 1 MB (matches suggestions.py)

_CATEGORY_STYLE = {
    "HIGH": "bold red",
    "MEDIUM": "bold yellow",
    "LOW": "bold green",
}

_TOP_N = 5

# Detectors that surface virtual environments.  Cache / artifact detectors
# are intentionally excluded from doctor – use `killpy clean` for those.
_CACHE_ARTIFACT_TYPES: frozenset[str] = frozenset({"cache", "artifacts"})
_ENV_TYPES: set[str] = {
    cls.name for cls in ALL_DETECTORS if cls.name not in _CACHE_ARTIFACT_TYPES
}


@click.command("doctor")
@click.option(
    "--path",
    default=Path.cwd,
    type=click.Path(path_type=Path, exists=True, file_okay=False, dir_okay=True),
    help="Root directory to scan.",
)
@click.option(
    "--json",
    "as_json",
    is_flag=True,
    default=False,
    help="Output as JSON.",
)
@click.option(
    "--all",
    "show_all",
    is_flag=True,
    default=False,
    help="Show all environments (MEDIUM and LOW included), not just the top offenders.",
)
def doctor_cmd(path: Path, as_json: bool, show_all: bool) -> None:
    """Analyse environments and show actionable deletion recommendations."""
    console = Console()

    scanner = Scanner(types=_ENV_TYPES)
    envs = scanner.scan(path)

    if not envs:
        if as_json:
            click.echo(
                json.dumps({"message": "No environments found.", "suggestions": []})
            )
        else:
            console.print("[yellow]No environments found.[/yellow]")
        return

    scored_envs = score_all(envs, run_git=True)
    engine = SuggestionEngine()
    suggestions = engine.classify_all(scored_envs)

    if as_json:
        _output_json(suggestions, envs)
        return

    _output_rich(console, suggestions, scored_envs, path, show_all=show_all)


# ---------------------------------------------------------------------------
# Output helpers
# ---------------------------------------------------------------------------


def _output_json(suggestions: list[Suggestion], envs) -> None:  # type: ignore[type-arg]
    total_size = sum(e.size_bytes for e in envs)
    env_by_path = {e.path: e for e in envs}
    high = [s for s in suggestions if s.category == "HIGH"]
    wasted = sum(
        env_by_path[s.env_path].size_bytes
        for s in high
        if s.env_path in env_by_path
        and env_by_path[s.env_path].size_bytes >= _IMPACTFUL_SIZE_BYTES
    )
    ignored_small = sum(1 for e in envs if e.size_bytes < _SMALL_SIZE_BYTES)
    data = {
        "total_environments": len(envs),
        "total_size_bytes": total_size,
        "total_size_human": format_size(total_size),
        "wasted_size_bytes": wasted,
        "wasted_size_human": format_size(wasted),
        "ignored_small_envs_count": ignored_small,
        "counts": {
            "HIGH": sum(1 for s in suggestions if s.category == "HIGH"),
            "MEDIUM": sum(1 for s in suggestions if s.category == "MEDIUM"),
            "LOW": sum(1 for s in suggestions if s.category == "LOW"),
        },
        "suggestions": [
            {
                "env_path": str(s.env_path),
                "score": s.score,
                "category": s.category,
                "reasons": s.reasons,
                "recommended_action": s.recommended_action,
            }
            for s in suggestions
        ],
    }
    click.echo(json.dumps(data, indent=2))


def _output_rich(
    console: Console,
    suggestions: list[Suggestion],
    scored_envs,  # type: ignore[type-arg]
    path: Path,
    *,
    show_all: bool = False,
) -> None:
    total_size = sum(se.env.size_bytes for se in scored_envs)
    high_suggestions = [s for s in suggestions if s.category == "HIGH"]
    high_paths = {s.env_path for s in high_suggestions}
    wasted = sum(
        se.env.size_bytes
        for se in scored_envs
        if se.env.path in high_paths and se.env.size_bytes >= _IMPACTFUL_SIZE_BYTES
    )

    console.print()
    console.rule("[bold cyan]Environment Health Report[/bold cyan]")
    console.print(
        f"\nScanned: [bold]{path}[/bold]\n"
        f"Environments found: [bold]{len(scored_envs)}[/bold]  |  "
        f"Total size: [bold]{format_size(total_size)}[/bold]  |  "
        f"Estimated wasted: [bold red]{format_size(wasted)}[/bold red]\n"
    )

    # Category summary
    counts = {
        "HIGH": sum(1 for s in suggestions if s.category == "HIGH"),
        "MEDIUM": sum(1 for s in suggestions if s.category == "MEDIUM"),
        "LOW": sum(1 for s in suggestions if s.category == "LOW"),
    }
    console.print(
        f"  [bold red]HIGH[/bold red] (safe to delete): {counts['HIGH']}  "
        f"[bold yellow]MEDIUM[/bold yellow] (review): {counts['MEDIUM']}  "
        f"[bold green]LOW[/bold green] (keep): {counts['LOW']}\n"
    )

    # Build suggestion lookup by env path
    suggestion_by_path = {s.env_path: s for s in suggestions}

    if show_all:
        # Show all environments grouped by category
        for category in ("HIGH", "MEDIUM", "LOW"):
            cat_suggestions = [s for s in suggestions if s.category == category]
            if not cat_suggestions:
                continue
            cat_paths = {s.env_path for s in cat_suggestions}
            cat_scored = [se for se in scored_envs if se.env.path in cat_paths]
            _print_category_table(console, category, cat_scored, suggestion_by_path)
    else:
        # Top offenders table (default)
        top = UsageTracker.get_top_offenders(scored_envs, n=_TOP_N)
        top_paths = {se.env.path for se in top}
        top_suggestion_map = {
            s.env_path: s for s in suggestions if s.env_path in top_paths
        }

        table = Table(
            show_header=True,
            header_style="bold cyan",
            title=f"Top {_TOP_N} Offenders",
            expand=False,
        )
        table.add_column("Path", no_wrap=False, min_width=20)
        table.add_column("Size", justify="right", min_width=8)
        table.add_column("Age (days)", justify="right", min_width=10)
        table.add_column("Score", justify="right", min_width=7)
        table.add_column("Category", min_width=8)

        now = datetime.now(tz=timezone.utc)
        for se in top:
            la = se.env.last_accessed
            if la.tzinfo is None:
                la = la.replace(tzinfo=timezone.utc)
            age_days = (now - la).days
            cat = top_suggestion_map.get(se.env.path)
            category_str = cat.category if cat else "—"
            style = _CATEGORY_STYLE.get(category_str, "")
            table.add_row(
                str(se.env.path),
                se.env.size_human,
                str(age_days),
                f"{se.score:.2f}",
                f"[{style}]{category_str}[/{style}]",
            )

        console.print(table)

    # Actionable recommendation
    if counts["HIGH"] > 0:
        console.print(
            f"\n[bold]Recommendation:[/bold] "
            f"Run [cyan]`killpy delete --older-than 180`[/cyan] "
            f"to free up to [bold red]{format_size(wasted)}[/bold red]."
        )
    elif counts["MEDIUM"] > 0:
        console.print(
            "\n[bold]Recommendation:[/bold] "
            "Review [yellow]MEDIUM[/yellow] environments before deleting."
        )
    else:
        console.print(
            "\n[bold green]All environments appear to be in active use.[/bold green]"
        )
    if not show_all and (counts["MEDIUM"] > 0 or counts["LOW"] > 0):
        hidden = counts["MEDIUM"] + counts["LOW"]
        console.print(
            f"[dim]({hidden} MEDIUM/LOW environment(s) hidden"
            " — run with [bold]--all[/bold] to see them)[/dim]"
        )
    console.print()


def _print_category_table(
    console: Console,
    category: str,
    scored_envs,  # type: ignore[type-arg]
    suggestion_by_path: dict,
) -> None:
    """Render a Rich table for a single suggestion category."""
    style = _CATEGORY_STYLE.get(category, "")
    titles = {
        "HIGH": "HIGH — Safe to delete",
        "MEDIUM": "MEDIUM — Review recommended",
        "LOW": "LOW — Likely in active use",
    }
    table = Table(
        show_header=True,
        header_style="bold cyan",
        title=f"[{style}]{titles.get(category, category)}[/{style}]",
        expand=False,
    )
    table.add_column("Path", no_wrap=False, min_width=20)
    table.add_column("Size", justify="right", min_width=8)
    table.add_column("Age (days)", justify="right", min_width=10)
    table.add_column("Score", justify="right", min_width=7)
    table.add_column("Reason", min_width=20)

    now = datetime.now(tz=timezone.utc)
    for se in scored_envs:
        la = se.env.last_accessed
        if la.tzinfo is None:
            la = la.replace(tzinfo=timezone.utc)
        age_days = (now - la).days
        suggestion = suggestion_by_path.get(se.env.path)
        reason = "; ".join(suggestion.reasons) if suggestion else ""
        table.add_row(
            str(se.env.path),
            se.env.size_human,
            str(age_days),
            f"{se.score:.2f}",
            reason,
        )

    console.print(table)
    console.print()
