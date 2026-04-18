# CLI

## Top-level command

The top-level command lives in `killpy/__main__.py` and does one of two things:

- launches the TUI by default
- runs a non-interactive bulk delete flow when `--delete-all` is provided

Examples:

```bash
killpy
```

```bash
killpy --path ~ --exclude "archive,backups"
```

```bash
killpy --path ~/projects --delete-all --yes
```

## `killpy list`

Use `list` when you want read-only inspection.

```bash
killpy list --path ~/projects
killpy list --type venv --type conda
killpy list --older-than 90
killpy list --json
killpy list --json-stream
```

`--json-stream` emits NDJSON progressively while the scan runs.

## `killpy delete`

Use `delete` when you want a scriptable delete flow with filtering.

```bash
killpy delete --path ~/projects --dry-run
killpy delete --path ~/projects --type cache --older-than 30
killpy delete --path ~/projects --yes
```

## `killpy stats`

Use `stats` to aggregate counts and sizes by detected type.

```bash
killpy stats --path ~/projects
killpy stats --json
```

## `killpy clean`

Use `clean` to recursively remove `__pycache__` directories.

```bash
killpy clean --path ~/projects
```

This command is narrower than the full cache detector model. It does not currently remove every cache type that the scanner can detect.

## `killpy stats`

Use `stats` to aggregate counts and sizes by detected type.

```bash
killpy stats --path ~/projects
killpy stats --json
killpy stats --history           # show cumulative scan history from ~/.killpy/history.json
```

The `--history` flag reads from the tracker database (`~/.killpy/history.json`) and shows aggregated totals across all past scans and deletions — useful to see how much space has been reclaimed over time.

## `killpy doctor`

Use `doctor` to get a smart health report that scores and prioritises environments for deletion.

```bash
killpy doctor                           # top 5 offenders in current directory
killpy doctor --path ~/projects         # scan a specific directory
killpy doctor --all                     # full report grouped by category
killpy doctor --json                    # machine-readable JSON output
```

### How scoring and classification work

`doctor` processes environments in two phases.

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

The score is used **only for ordering** results within the same category (highest score shown first). It does not determine the category.

**Phase 2 — Rule-based classification**

The category is assigned deterministically by evaluating rules in order:

| Priority | Condition | Category |
|----------|-----------|----------|
| 1 | `is_orphan == True` **and** `age ≥ 180 days` | `HIGH` |
| 2 | `has_project_files == False` **and** `age ≥ 365 days` | `HIGH` |
| 3 | `git.is_active == True` **or** `age < 120 days` | `LOW` |
| 4 | `age ≥ 120 days` | `MEDIUM` |
| 5 | *(fallback)* | `LOW` |

Age and orphan status dominate. Size has **no effect** on the category.

| Category | Recommended action |
|----------|--------------------|
| `HIGH` | Delete — unused and orphaned |
| `MEDIUM` | Review — possibly unused |
| `LOW` | Keep — actively used / Keep |

Environments are classified into three categories:

| Category | Meaning |
|----------|---------|
| `HIGH` | Delete — unused and orphaned (age + orphan status dominate). |
| `MEDIUM` | Review — possibly unused (moderately stale, no strong active signal). |
| `LOW` | Keep — actively used or recently accessed. |

### Default output

Shows the **Top 5 Offenders** table (highest-scoring environments) with a hint if MEDIUM or LOW environments exist but are hidden:

```
(12 MEDIUM/LOW environment(s) hidden — run with --all to see them)
```

### `--all` flag

Renders three separate tables — HIGH, MEDIUM, and LOW — each showing Path, Size, Age, Score, and Reason columns.

```bash
killpy doctor --path ~ --all
```

### JSON output

```bash
killpy doctor --json | jq '.suggestions[] | select(.category=="HIGH") | .env_path'
```

The JSON payload includes:

- `total_environments`, `total_size_bytes/human`
- `wasted_size_bytes/human` (sum of HIGH environments)
- `counts` breakdown by category
- `suggestions` array with `env_path`, `score`, `category`, `reasons`, `recommended_action`
