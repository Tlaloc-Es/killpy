---
title: CLI reference — every killpy command and flag
description: Every killpy subcommand in one place — list, find, delete, stats, clean, and doctor — with usage examples, flags, and JSON output options.
---

# CLI reference

Complete reference for every `killpy` subcommand and flag.

## `killpy` — launch TUI or headless delete

The top-level command lives in `killpy/__main__.py` and does one of two things:

- launches the TUI by default
- runs a non-interactive bulk delete flow when `--delete-all` is provided

```
Usage: killpy [OPTIONS] COMMAND [ARGS]...

Options:
  --path DIRECTORY      Root directory to scan  [default: cwd]
  -E, --exclude TEXT    Comma-separated path patterns to skip
                        e.g. --exclude "backups,legacy"
  -D, --delete-all      Scan and delete ALL found environments without
                        launching the TUI
  -y, --yes             Skip confirmation prompt (use with --delete-all)
  --force               With --delete-all: also delete environments
                        currently in use (⚠ system-critical)
  --help                Show this message and exit.
```

Examples:

```bash
killpy                                        # TUI, scan cwd
killpy --path ~                               # TUI, scan home
killpy --path ~/projects --exclude "legacy"   # TUI, skip paths with "legacy"
killpy --path ~ --exclude "archive,backups"   # multiple patterns
killpy --path ~/projects --delete-all         # headless, with confirmation
killpy --path ~/projects --delete-all --yes   # fully automated, no prompt
```

## `killpy list` — inspect environments

![killpy list](https://raw.githubusercontent.com/Tlaloc-Es/killpy/master/docs/gifs/list.gif)

Use `list` when you want read-only inspection.

```bash
killpy list                               # list all detected environments
killpy list --path ~/projects             # scan a specific path
killpy list --type venv --type conda      # filter by type (repeatable)
killpy list --older-than 90               # not modified in the last 90 days
killpy list --min-size 500MB              # at least 500 MB large
killpy list --sort date                   # sort by date (newest first)
killpy list --sort name --reverse         # sort by name Z-A
killpy list --json                        # output as a JSON array
killpy list --json-stream                 # stream as NDJSON — one line per env
killpy list --quiet                       # suppress progress output (scripts/CI)
```

While scanning, `killpy list` shows a live progress indicator on **stderr** so you can see which detector is running. Stdout receives only the final output (table, JSON, or NDJSON), so pipes and redirections are never polluted. Use `--quiet` / `-q` to silence the progress indicator entirely (useful in scripts or CI).

The **Path** column mirrors the form of `--path`: a relative `--path` produces relative paths, an absolute one produces absolute paths (long paths are truncated to keep rows compact). The full absolute path is always available via `--json` / `--json-stream` in the `absolute_path` field.

`--json` example output:

```json
[
  {
    "path": "projects/my-app/.venv",
    "absolute_path": "/home/user/projects/my-app/.venv",
    "name": "my-app/.venv",
    "type": "venv",
    "last_modified": "2025-11-02T14:23:01+00:00",
    "size_bytes": 54393984,
    "size_human": "51.88 MB",
    "managed_by": null,
    "is_system_critical": false
  }
]
```

`--json-stream` emits NDJSON progressively while the scan runs — ideal for piping into `jq` or processing in scripts before the full scan completes. Note that `--sort` applies to the table and `--json` output only: the stream always emits in detection order, since a global sort would require buffering the whole scan.

```bash
killpy list --json-stream --path ~ | jq 'select(.type == "conda") | .size_human'
```

![killpy list --json](https://raw.githubusercontent.com/Tlaloc-Es/killpy/master/docs/gifs/list-json.gif)

## `killpy find` — locate environments with a package

![killpy find](https://raw.githubusercontent.com/Tlaloc-Es/killpy/master/docs/gifs/find.gif)

Find every environment that has a given package installed. `PACKAGE` accepts
standard PEP 508 / uv-style version specifiers.

```bash
killpy find requests                      # any version of requests
killpy find "flask>=1.0"                   # version specifier
killpy find "numpy>=1.24,<2.0"             # combined constraints
killpy find "django==4.2.*"                # wildcard match
killpy find "scipy~=1.11"                  # compatible release
```

Optional flags:

```bash
# Limit the scan to a specific root directory
killpy find "fastapi>=0.100" --path ~/projects

# Filter by environment type (repeatable)
killpy find torch --type venv --type conda

# Search only environments at least 1.5 GB large
killpy find torch --min-size 1.5GB

# Machine-readable output
killpy find "numpy>=2" --json
```

The command reads `*.dist-info/METADATA` files from each environment's `site-packages` directory — no interpreter invocation is needed.

## `killpy delete` — remove environments

![killpy delete](https://raw.githubusercontent.com/Tlaloc-Es/killpy/master/docs/gifs/delete.gif)

Use `delete` when you want a scriptable delete flow with filtering.

```bash
killpy delete                             # interactive confirmation before delete
killpy delete --yes                       # skip confirmation
killpy delete --dry-run                   # preview — nothing is deleted
killpy delete --type venv                 # only a specific type
killpy delete --type venv --type cache    # multiple types
killpy delete --older-than 180 --yes      # delete stale envs, no prompt
killpy delete --min-size 500MB --dry-run  # preview only large environments
killpy delete --force                     # include in-use (⚠) environments
killpy delete --path ~/projects
```

Environments currently in use (the one killpy runs from, or the pyenv global version) are flagged system-critical and **skipped by default** — they are listed as "currently in use" and only deleted when `--force` is given. The same applies to `killpy --delete-all`.

After a successful delete in an interactive terminal, killpy prints one final line with the total space freed and the project URL. It is suppressed automatically when stdout is not a TTY (pipes, scripts) or when the `CI` environment variable is set, and can be disabled permanently with `KILLPY_NO_HINT=1`.

## `killpy stats` — disk usage summary

![killpy stats](https://raw.githubusercontent.com/Tlaloc-Es/killpy/master/docs/gifs/stats.gif)

Use `stats` to aggregate counts and sizes by detected type.

```bash
killpy stats
killpy stats --path ~/projects
killpy stats --min-size 500MB     # aggregate only large environments
killpy stats --json
killpy stats --history           # cumulative scan history
```

The `--history` flag reads from the tracker database (`~/.killpy/history.json`) and shows aggregated totals across all past scans and deletions — useful to see how much space has been reclaimed over time.

Example output:

```
         Environment stats
┌──────────────┬───────┬────────────┬──────────┐
│ Type         │ Count │ Total size │ Avg size │
├──────────────┼───────┼────────────┼──────────┤
│ venv         │    12 │    4.2 GB  │  350 MB  │
│ conda        │     3 │    2.1 GB  │  700 MB  │
│ cache        │    45 │  890.0 MB  │   20 MB  │
│ poetry       │     6 │  750.0 MB  │  125 MB  │
└──────────────┴───────┴────────────┴──────────┘

Total: 66 environment(s) — 7.9 GB
```

## `killpy clean` — remove cache directories

![killpy clean](https://raw.githubusercontent.com/Tlaloc-Es/killpy/master/docs/gifs/clean.gif)

```bash
killpy clean
killpy clean --path ~/projects
```

Removes `__pycache__` directories recursively under the target path. This command is narrower than the full cache detector model — it does not currently remove every cache type that the scanner can detect.

## `killpy doctor` — smart health report

```
Usage: killpy doctor [OPTIONS]

Options:
  --path DIRECTORY  Root directory to scan  [default: cwd]
  --min-size SIZE   Only analyse environments at least this large (for example,
                    500MB or 1.5GB).
  --all             Show all environments grouped by category
                    (HIGH / MEDIUM / LOW). Default shows only the top 5.
  --json            Output as JSON.
  --help            Show this message and exit.
```

![killpy doctor](https://raw.githubusercontent.com/Tlaloc-Es/killpy/master/docs/gifs/doctor.gif)

`--min-size` accepts case-insensitive binary size units (`B`, `KB`, `MB`, `GB`,
or `TB`) and decimal values such as `1.5GB`. Invalid values fail with a usage
error. The option is also available on `list`, `find`, `delete`, and `stats`.

`doctor` analyses every detected virtual environment in two phases.

### How scoring and classification work

**Phase 1 — Scoring (for sorting only)**

Each environment receives a numeric score between 0 and 1 computed from four weighted signals:

| Signal | Weight | Description |
|--------|--------|-------------|
| **Size** | 0.25 | Sigmoid-normalised around 500 MB. A 500 MB env scores ≈ 0.5. |
| **Age** | 0.30 | Linear: `min(age_days / 365, 1.0)`. Caps at 1.0 after a year. |
| **Orphan status** | 0.25 | `1.0` when no `pyproject.toml`, `requirements.txt`, `setup.py`, `Pipfile`, `.python-version`, or `setup.cfg` is found in the env dir or its parent. `0.0` otherwise. |
| **Git inactivity** | 0.20 | `0.0` = active repo, `1.0` = repo exists but inactive, `0.5` = unknown or no repo. |

The weighted average is:

```
score = (0.25 × size_score + 0.30 × age_score + 0.25 × orphan_score + 0.20 × git_score) / 1.0
```

The score is used **only for ordering** results within the same category (highest score shown first). It does **not** determine the category itself.

**Phase 2 — Rule-based classification**

The category is assigned deterministically by evaluating rules in order:

| Priority | Condition | Category |
|----------|-----------|----------|
| 1 | `is_orphan == True` **and** `age ≥ 180 days` | `HIGH` |
| 2 | `git.is_active == True` **or** `age < 120 days` | `LOW` |
| 3 | `age ≥ 120 days` *(exhaustive fallback)* | `MEDIUM` |

Age and orphan status are the dominant signals. Size has **no effect** on the category.

| Category | Recommended action |
|----------|--------------------|
| `HIGH` | Delete — unused and orphaned (age + orphan status dominate) |
| `MEDIUM` | Review — possibly unused (moderately stale, no strong active signal) |
| `LOW` | Keep — active git repo or recently modified |

### Examples

```bash
killpy doctor                           # top 5 offenders in current directory
killpy doctor --path ~                  # scan home folder
killpy doctor --all                     # show all environments by category
killpy doctor --json                    # machine-readable output
killpy doctor --path ~/projects --all   # full report for a specific tree
```

### Default output

Shows the **Top 5 Offenders** table (highest-scoring environments) with a hint if MEDIUM or LOW environments exist but are hidden:

```
──────────── Environment Health Report ────────────
Scanned: /home/user/projects
Environments found: 18  |  Total size: 6.2 GB  |  Estimated wasted: 3.8 GB
  HIGH (safe to delete): 5  MEDIUM (review): 7  LOW (keep): 6

               Top 5 Offenders
┌──────────────────────────┬────────┬───────────┬───────┬──────────┐
│ Path                     │   Size │ Age (days)│ Score │ Category │
├──────────────────────────┼────────┼───────────┼───────┼──────────┤
│ ~/old-project/.venv      │ 850 MB │       312 │  0.94 │ HIGH     │
│ ~/tutorial2023/.venv     │ 420 MB │       198 │  0.87 │ HIGH     │
└──────────────────────────┴────────┴───────────┴───────┴──────────┘

Recommendation: Run `killpy delete --older-than 180` to free up to 3.8 GB.
(12 MEDIUM/LOW environment(s) hidden — run with --all to see them)
```

### `--all` flag

Renders three separate tables — HIGH, MEDIUM, and LOW — each showing Path, Size, Age, Score, and Reason columns.

```bash
killpy doctor --path ~ --all
```

### JSON output

The JSON output is useful for scripting or auditing:

```bash
killpy doctor --json | jq '.suggestions[] | select(.category=="HIGH") | .env_path'
```

The JSON payload includes:

- `total_environments`, `total_size_bytes/human`
- `wasted_size_bytes/human` (sum of HIGH environments)
- `counts` breakdown by category
- `suggestions` array with `env_path`, `score`, `category`, `reasons`, `recommended_action`
