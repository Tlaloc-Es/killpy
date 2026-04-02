# Architecture Overview

`killpy` is structured around a simple pipeline:

1. A `Scanner` chooses applicable detectors.
1. Each detector returns `Environment` objects.
1. Results are deduplicated by resolved path.
1. The TUI or CLI command renders or filters those results.
1. A `Cleaner` applies the right deletion strategy for each entry.

## Core pieces

### `Environment`

The shared data model lives in `killpy/models.py`. It carries:

- path
- name
- type
- last access timestamp
- size in bytes
- optional `managed_by` metadata
- a system-critical flag used by the UI

### `Scanner`

The scanner lives in `killpy/scanner.py`.

It supports:

- synchronous scanning for commands such as `list`, `delete`, and `stats`
- asynchronous progressive scanning for the TUI
- exclusion filtering
- deduplication
- system-critical environment marking

### Detectors

Each detector lives in `killpy/detectors/` and is responsible for one source of truth, such as filesystem walking or external command output.

### `Cleaner`

The cleaner lives in `killpy/cleaner.py`.

Deletion strategy depends on the item:

- `conda` entries are removed through `conda env remove`
- `pipx` entries are removed through `pipx uninstall`
- everything else defaults to filesystem removal

## Why this split works

The current layout keeps detection logic isolated from UI and command rendering. That makes it easier to add detectors, extend JSON output, or improve TUI behavior without rewriting the whole stack.
