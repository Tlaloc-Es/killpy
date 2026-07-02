# Detector Types

The scanner registers detectors in `killpy/detectors/__init__.py`.

## Environment-oriented detectors

- `venv`: local `.venv` directories and directories containing `pyvenv.cfg`
- `poetry`: Poetry environments stored in the Poetry cache directory
- `conda`: environments returned by `conda env list`
- `pipx`: environments returned by `pipx list --json`
- `pyenv`: versions installed under the pyenv versions directory
- `pipenv`: Pipenv virtual environments
- `hatch`: Hatch environments
- `uv`: environments managed by uv itself — tool environments from `uv tool install` (removed via `uv tool uninstall`) and Python versions from `uv python install`, both under `~/.local/share/uv`. Project virtualenvs created by `uv venv` / `uv sync` are regular `.venv` directories and are reported by the `venv` detector
- `tox`: tox environments

## Additional scanner-only categories

- `cache`: local cache directories such as `__pycache__`, `.pytest_cache`, `.mypy_cache`, `.ruff_cache`, plus the global pip/uv caches. The global caches are only included when they live inside the scanned path (e.g. `--path ~`) — a scan scoped to a repository never surfaces or deletes them
- `artifacts`: build output directories such as `dist`, `build`, `.egg-info`, and `.dist-info`

## Notes on presentation

- The synchronous scanner and CLI commands can include all detector categories.
- The current TUI explicitly initializes its scanner with environment-oriented detector types plus `pipx`, not cache and artifact categories.

## Notes on deletion

- Tool-managed entries can use an external deletion strategy.
- Most filesystem-backed entries are removed recursively from disk.
