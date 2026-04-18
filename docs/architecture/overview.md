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

## Intelligence layer

The `killpy/intelligence/` package adds smart scoring and recommendations on top of raw scan results.

### Components

| Module | Responsibility |
|--------|---------------|
| `scoring.py` | Computes a numeric score 0–1 per environment from size, age, orphan status, and git inactivity. Used for sorting only. |
| `suggestions.py` | Classifies scored environments into HIGH / MEDIUM / LOW using deterministic rules based on age and orphan status. Size does not affect category. |
| `tracker.py` | Persists scan and deletion history to `~/.killpy/history.json` for cumulative reporting. |
| `git_analyzer.py` | Detects the nearest git repository for an environment and checks whether it is actively used. |

### Data flow

```
Scanner.scan()
    └─> score_all(envs)                      # ScoredEnv list (sorted by score desc)
        └─> SuggestionEngine.classify_all()  # Suggestion list (sorted HIGH → MEDIUM → LOW)
            └─> doctor_cmd renders tables / JSON
```

The `UsageTracker` records each scan in `~/.killpy/history.json` and is queried by `killpy stats --history`.

### Score computation

The score is a weighted average of four normalised signals:

| Signal | Weight | Notes |
|--------|--------|-------|
| Size | 0.25 | Sigmoid-normalised around 500 MB |
| Age | 0.30 | Linear, caps at 1.0 after 365 days |
| Orphan status | 0.25 | 1.0 if no project marker found nearby, 0.0 otherwise |
| Git inactivity | 0.20 | 0.0 = active, 1.0 = inactive, 0.5 = unknown |

The score determines *sort order* within each category. It does **not** determine the category.

### Classification rules

`SuggestionEngine.classify()` applies rules in strict priority order:

1. **HIGH** — `is_orphan == True` and `age ≥ 180 days`
1. **HIGH** — `has_project_files == False` and `age ≥ 365 days`
1. **LOW** — `git.is_active == True` or `age < 120 days`
1. **MEDIUM** — `age ≥ 120 days`
1. **LOW** — fallback

Age and orphan status dominate. Size does not affect classification.

### `Suggestion` model

Each `Suggestion` carries:

- `env_path` — the environment being evaluated
- `score` — float 0–1 (higher = more wasteful)
- `category` — `"HIGH"`, `"MEDIUM"`, or `"LOW"`
- `reasons` — list of human-readable strings explaining the score
- `recommended_action` — short action string (e.g. `"delete"`, `"review"`, `"keep"`)
