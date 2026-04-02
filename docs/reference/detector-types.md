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
- `uv`: uv environments
- `tox`: tox environments

## Additional scanner-only categories

- `cache`: local and global cache directories such as `__pycache__`, `.pytest_cache`, `.mypy_cache`, `.ruff_cache`, and selected global tool caches
- `artifacts`: build output directories such as `dist`, `build`, `.egg-info`, and `.dist-info`

## Notes on presentation

- The synchronous scanner and CLI commands can include all detector categories.
- The current TUI explicitly initializes its scanner with environment-oriented detector types plus `pipx`, not cache and artifact categories.

## Notes on deletion

- Tool-managed entries can use an external deletion strategy.
- Most filesystem-backed entries are removed recursively from disk.
