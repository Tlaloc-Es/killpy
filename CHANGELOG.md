## 0.11.0b2 (2025-01-17)

## 0.11.0b1 (2025-01-17)

## 0.11.0b0 (2025-01-17)

### Feat

- add GitHub Actions workflow for version bumping and changelog generation
- add support for pipx package management and enhance virtual environment tab functionality

### Refactor

- separate entities

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
