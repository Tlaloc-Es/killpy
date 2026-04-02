# Filtering and Selection

## Excluding paths

The top-level command accepts comma-separated exclusion patterns:

```bash
killpy --path ~ --exclude "archive,backups,legacy"
```

Those exclusions are applied by substring matching against discovered paths.

## Filtering by age

The `list` and `delete` commands support `--older-than`:

```bash
killpy list --older-than 90
killpy delete --older-than 180 --dry-run
```

This filter is based on the recorded last-accessed timestamp stored in each `Environment` object.

## Regex filtering in the TUI

Press `/` in the TUI to filter visible rows by path. The filter uses regular expressions and updates the environment table live.

Examples:

```text
django
```

```text
/(api|worker|etl)/
```

If the regex is invalid, the TUI falls back to showing all rows.

## Multi-select workflow

1. Press `t` to enable multi-select mode.
1. Press `Space` to toggle individual rows.
1. Press `a` to select or deselect all visible non-deleted rows.
1. Press `Ctrl+d` to delete the selected set.

The multi-select model operates on the currently visible rows, so active filtering can help narrow large scans before deletion.
