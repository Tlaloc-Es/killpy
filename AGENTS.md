# AGENTS.md

## Project Overview

`killpy` is a Python CLI/TUI utility to find and remove Python-related environments and free disk space.

Main capabilities:

- Discover local virtual environments (`.venv` and folders containing `pyvenv.cfg`)
- Discover Conda environments
- Discover Poetry virtualenvs
- Discover installed `pipx` packages and uninstall them
- Remove `__pycache__` directories

Primary UX:

- Interactive terminal UI (Textual app) for listing and deleting environments
- CLI command to clean caches (`killpy clean`)

## Goal

Help users reclaim disk space safely by surfacing Python environments with size info and allowing explicit deletion actions.

## Tech Stack

- Python `>=3.12`
- `click` for CLI command routing
- `textual` for interactive terminal UI
- `rich` as a dependency used by Textual ecosystem and terminal rendering

Reference links:

- Textual docs: https://textual.textualize.io/
- Textual repository: https://github.com/Textualize/textual
- Rich docs: https://rich.readthedocs.io/en/latest/introduction.html
- Rich repository: https://github.com/Textualize/rich

Packaging and tooling:

- `pyproject.toml` (PEP 621 metadata)
- `uv` support (`[tool.uv] package = true`)
- Commit/version workflow via `commitizen`
- Lint/type/test dev tooling declared under `[dependency-groups].dev`

## Repository Structure

Top-level:

- `pyproject.toml` — package metadata, dependencies, scripts, tool config
- `README.md` — user documentation
- `CHANGELOG.md` — release history
- `.github/workflows/` — CI/release automation

Package layout (`killpy/`):

- `__main__.py` — CLI entrypoint (`killpy` script); registers all subcommands
- `cli.py` — Textual app (`TableApp`) and interactive actions
- `models.py` — `Environment` dataclass (shared contract between all layers)
- `scanner.py` — `Scanner`: orchestrates detectors, deduplicates results
- `cleaner.py` — `Cleaner`: handles deletion (shutil.rmtree or pipx uninstall)
- `commands/clean.py` — `killpy clean` subcommand
- `commands/delete.py` — `killpy delete` subcommand
- `commands/list.py` — `killpy list` subcommand
- `commands/stats.py` — `killpy stats` subcommand
- `cleaners/__init__.py` — `remove_pycache` helper
- `files/__init__.py` — file-size helpers (`get_total_size`, `format_size`)
- `detectors/` — one detector class per environment type:
  - `base.py` — `AbstractDetector` interface
  - `venv.py` — `.venv` dirs and `pyvenv.cfg`-based envs
  - `pyenv.py` — pyenv-managed Python versions
  - `poetry.py` — Poetry global virtualenv cache
  - `conda.py` — Conda environments
  - `pipx.py` — pipx packages
  - `hatch.py` — Hatch environments
  - `pipenv.py` — Pipenv virtualenvs
  - `tox.py` — tox `.tox` directories
  - `uv.py` — uv `.uv` directories
  - `artifacts.py` — build artifacts (`dist/`, `build/`, `*.egg-info`)
  - `cache.py` — cache dirs (`__pycache__`, `.mypy_cache`, `.pytest_cache`, …)

## Runtime Flow (Important for Agents)

1. User runs `killpy`.
1. `killpy.__main__.cli` launches `TableApp`.
1. `TableApp` renders UI immediately, then starts background scanning.
1. Results are appended progressively to tables while scanning continues.
1. User can mark/delete envs or uninstall pipx packages.

Recent behavior to preserve:

- Non-blocking startup with visible loading state
- No forced tab/focus jumps during background loading
- Compact path display in venv table with full selected path shown separately
- `--path` option for `killpy` root scan path (defaults to current directory)

## CLI Surface

Main command:

- `killpy`
- `killpy --path /some/folder`

Subcommand:

- `killpy clean`
- `killpy clean --path /some/folder`

## Key Data Shapes

Venv-like rows are expected as tuples:

- `(path, type, last_modified, size_bytes, size_human)`

Pipx rows are expected as tuples:

- `(package_name, size_bytes, size_human)`

The UI appends a status column at render-time.

## Conventions and Guardrails

- Keep changes minimal and focused; avoid broad refactors.
- Preserve keyboard bindings and existing interaction model unless explicitly requested.
- Prefer instance-level mutable state in `TableApp` (avoid mutable class attributes).
- Avoid global logging side-effects at import time.
- Handle missing tools (`conda`, `pipx`, Poetry dirs) gracefully.
- For long-running scans, prioritize perceived responsiveness.

## Development Notes

- If running locally without dependencies, UI imports may fail until package deps are installed.

- Syntax validation shortcut:

  - `uv python -m compileall killpy`

- Typical local install/dev workflows:

  - `pip install -e .`
  - or use `uv`-based workflows for dependency management/build.

## Suggested Agent Tasks

Good first tasks for coding agents:

- Improve robustness of parsers for external command output (`conda`, `pipx`)
- Add or improve tests around tuple shape assumptions and path handling
- Keep README examples aligned with CLI options
- Improve UX messages while preserving compact layout
