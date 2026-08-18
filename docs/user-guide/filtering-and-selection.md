---
title: Filtering and selection — target exactly what to delete
description: Exclude paths, filter by age with --older-than or by size with --min-size, and use the TUI's live filter and multi-select to delete exactly the rows you intend.
---

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

This filter is based on the recorded last-modified timestamp (`st_mtime`) stored in each `Environment` object.

## Filtering by size

The `list`, `find`, `delete`, `stats` and `doctor` commands support `--min-size`, which keeps only environments at least that large:

```bash
killpy list --min-size 500MB             # only what is worth reclaiming
killpy delete --min-size 1GB --dry-run   # preview the big ones
```

Sizes take a unit (`B`, `KB`, `MB`, `GB` or `TB`, case-insensitive) and accept decimals such as `1.5GB`. Units are binary — `1KB` is 1024 bytes — so a threshold matches exactly what the tool prints in its `Size` column. A value without a unit is a usage error.

`killpy stats --history` reports stored totals rather than a fresh scan, so scan filters like `--min-size` and `--path` do not apply to it.

## Sorting output

The `list` command supports `--sort` (`size`, `date`, `name`) and `--reverse`:

```bash
killpy list --sort date                  # newest modified first
killpy list --sort size --reverse        # smallest size first
killpy list --sort name                  # alphabetical A-Z
```

Sorting applies to the table and `--json` output. `--json-stream` always emits in detection order — results stream out as each detector finishes.

## Path filtering in the TUI

Press `/` in the TUI to filter visible rows by path. The filter is a
case-insensitive substring match and updates the environment table live as you
type.

Examples:

```text
django
```

```text
projects/api
```

Any row whose path contains the typed text is kept; an empty query shows all
rows.

## Multi-select workflow

1. Press `t` to enable multi-select mode.
1. Press `Space` to toggle individual rows.
1. Press `a` to select or deselect all visible non-deleted rows.
1. Press `Ctrl+d` to delete the selected set.

The multi-select model operates on the currently visible rows, so active filtering can help narrow large scans before deletion.
