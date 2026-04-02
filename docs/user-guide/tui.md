# TUI

The default `killpy` command launches a Textual application defined in `killpy/cli.py`.

## What the TUI shows

- An `Environments` tab for virtual-environment style results
- A dedicated `Pipx` tab for `pipx` packages

The current TUI does not expose dedicated tables for cache directories or build artifacts, even though those are detectable in the scanner and CLI flows.

## Loading model

The TUI starts with an empty table and updates progressively while detector tasks finish. This is backed by the asynchronous `scan_async` flow in the scanner.

## Keyboard shortcuts

- `j` / `k`: move the cursor
- `/`: open the regex path filter
- `Escape`: clear and close the filter input
- `d`: mark an environment for deletion
- `Ctrl+d`: delete marked rows or all selected rows in multi-select mode
- `Shift+Delete`: delete the highlighted row immediately
- `t`: toggle multi-select mode
- `Space`: toggle the highlighted row in multi-select mode
- `a`: select or deselect all visible rows in multi-select mode
- `o`: open the parent directory of the selected environment
- `p`: remove `__pycache__` directories under the current scan root
- `u`: uninstall the selected `pipx` package from the `Pipx` tab
- `Ctrl+q`: quit the application

## Safety model

- Nothing is deleted merely by scanning.
- Rows can be marked and then confirmed for deletion.
- Some environments may be flagged as system-critical if they match the currently active runtime environment.
