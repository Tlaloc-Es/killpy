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
