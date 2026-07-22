## 1.0.1 (2026-07-22)

### Perf

- **scanner**: one shared filesystem walk for venv/cache/artifacts/tox (GIT-2)

## 1.0.0 (2026-07-21)

### BREAKING CHANGE

- the `killpy list --json` / `--json-stream` output field
`last_accessed` is renamed to `last_modified`. Scripts reading that key must
be updated.

### Refactor

- correct last_accessed→last_modified semantics; drop dead rule and ReDoS filter

## 0.25.1 (2026-07-21)

### Refactor

- align codebase consistency and dev-docs (no behavior change)

## 0.25.0 (2026-07-21)

### Feat

- **safety**: refuse insane rmtree targets (root, home, top-level, symlink)
- **safety**: skip in-use environments on delete unless --force

### Fix

- **files**: never follow symlinks when sizing trees or removing pycache
- harden conda parsing, pyenv global match, clean validation, freed bytes
- **detectors**: honour env overrides and platform default locations

## 0.24.2 (2026-07-02)

### Fix

- **uv**: detect real uv-managed assets instead of nonexistent .uv dirs
- **cache**: skip caches inside environments to avoid double counting
- **cache**: only surface global pip/uv caches when inside the scan path
- **delete-all**: handle deletion errors instead of crashing mid-run
- **tui**: make U key actually uninstall the selected pipx package
- **artifacts**: stop reporting venv internals as deletable build artifacts

### Refactor

- **doctor**: remove unreachable HIGH classification rule

## 0.24.1 (2026-07-02)

### Fix

- **tui**: track multi-select by path so sorting cannot delete wrong rows
- **history**: record scan sessions so stats --history works

## 0.24.0 (2026-04-23)

### Feat

- **list**: add --quiet option to suppress progress output

## 0.23.0 (2026-04-19)

### Feat

- **find**: implement `killpy find` command to locate environments with specific packages

## 0.22.0 (2026-04-19)

### Feat

- **pre-commit**: enhance hooks with detailed descriptions
- **commands**: add shared utility for filtering environments

## 0.21.0 (2026-04-18)

### Feat

- add intelligence layer with scoring, suggestions, and usage tracking

## 0.20.0 (2026-04-13)

## 0.19.2 (2026-04-10)

### Fix

- use timezone-aware datetimes for --older-than filtering

## 0.19.1 (2026-04-06)

### Fix

- logo

## 0.19.0 (2026-04-06)

### Feat

- add project URLs to pyproject.toml

## 0.18.0 (2026-04-01)

### Feat

- expand Python version support to 3.10+

## 0.17.0 (2026-04-01)

### Feat

- **cli**: enhance loading display with spinner and progress

## 0.16.0 (2026-03-22)

### Feat

- remove legacy code and clean repository structure

## 0.15.7 (2026-02-21)

### Fix

- structure

## 0.15.6 (2026-02-21)

### Fix

- #8 #11 #15

## 0.15.5 (2025-07-19)

### Fix

- set logging level to INFO in clean command for better visibility

## 0.15.4 (2025-02-07)

### Fix

- set logging level to INFO in clean command for better visibility

## 0.15.3 (2025-02-07)

### Fix

- enhance logging in clean command to report freed space

## 0.15.2 (2025-02-07)

### Fix

- update killpy entry in pre-commit hooks to use clean command

## 0.15.1 (2025-02-07)

### Fix

- update killpy entry point to use CLI

## 0.15.0 (2025-02-07)

### Feat

- add clean command to killpy and integrate with CLI

## 0.14.1 (2025-01-23)

### Fix

- the app breaks when 'pipx' is not installed. #14

## 0.14.0 (2025-01-17)

### Fix

- forcebump

## 0.13.0 (2025-01-17)

### Feat

- add GitHub Actions workflow for version bumping and changelog generation

### Fix

- forcebump
- update environment removal methods to use killers dictionary
- update import path for TableApp in main module

### Refactor

- separate entities

## 0.11.0b4 (2025-01-17)

### Feat

- add GitHub Actions workflow for version bumping and changelog generation

### Fix

- update environment removal methods to use killers dictionary
- update import path for TableApp in main module

### Refactor

- separate entities

## 0.11.0 (2025-01-16)

## 0.11.0b3 (2025-01-17)

## 0.11.0b2 (2025-01-17)

## 0.11.0b1 (2025-01-17)

## 0.11.0b0 (2025-01-17)

### Feat

- add GitHub Actions workflow for version bumping and changelog generation
- add support for pipx package management and enhance virtual environment tab functionality

### Refactor

- separate entities

## 0.11.0 (2025-01-16)

### Feat

- add support for pipx package management and enhance virtual environment tab functionality

## 0.10.0 (2025-01-06)

### Feat

- enhance README and add support for listing Poetry virtual environments

## 0.9.0 (2025-01-05)

### Feat

- add functionality to clean up __pycache__ directories and update README

## 0.8.4 (2025-01-05)

### Fix

- update sorting logic in find_venvs functions to sort by size

## 0.8.3 (2025-01-05)

### Fix

- handle FileNotFoundError in get_total_size and find_venvs functions close #4

## 0.8.2 (2025-01-05)

### Fix

- try to execute with pipx

## 0.8.1 (2025-01-05)

### Fix

- consolidate environment handling functions into __main__.py and remove envs_handler.py

## 0.8.0 (2025-01-05)

### Feat

- update references from 'KillPy' to 'killpy' across the project

## 0.7.0 (2025-01-05)

### Feat

- replace 'KillPy' with 'killpy' in workflow and pyproject.toml

## 0.6.0 (2025-01-05)

### Feat

- add KillPy script entry point to pyproject.toml

## 0.5.0 (2025-01-05)

### Feat

- enhance virtual environment management with deletion features and refactor code structure close #7

## 0.4.0 (2025-01-03)

### Feat

- implement asynchronous searching for virtual environments close #2

## 0.3.0 (2025-01-03)

### Feat

- add support for finding virtual environments with pyvenv and remove duplicates

### Fix

- remove click dependency and update package version to 0.2.1

## 0.2.2 (2025-01-03)

### Fix

- change key binding from 'ctrl+m' to 'space' for deleting .venv close #5

## 0.2.1 (2025-01-03)

### Fix

- fails if conda is not installed #3

## 0.2.0 (2025-01-03)

### Feat

- add support for listing and removing Conda environments in the app

## 0.1.7 (2025-01-02)

### Fix

- add a banner to TableApp for enhanced user interface

## 0.1.6 (2025-01-02)

### Fix

- enhance TableApp with improved venv display and deletion feedback

## 0.1.5 (2025-01-02)

### Refactor

- reorganize imports and update deleted_cells type annotation in TableApp
- improve find_venvs and get_total_size functions for better performance and readability

## 0.1.4 (2025-01-02)

### Fix

- rename script entry point from pykill to killpy in pyproject.toml

## 0.1.3 (2025-01-02)

### Fix

- rename script entry point from posewebcam to pykill in pyproject.toml

## 0.1.2 (2025-01-02)

### Fix

- prevent find_venvs from traversing subdirectories within `.venv` folders

## 0.1.1 (2025-01-02)

### Fix

- **cli**: fix command script
