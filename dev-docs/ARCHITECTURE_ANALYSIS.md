# Architecture Analysis — killpy

> **Audience:** Developers and coding agents contributing to killpy.
> **Purpose:** Honest diagnostic of the current architecture — what works, what
> doesn't, and what should be changed if the project keeps growing.
> **Date:** 2026-04-19 (original) · Status updated 2026-07-21

______________________________________________________________________

## Status update — 2026-07-21 consistency audit

Several issues below were fixed after this document was written. The sections
are kept for history, but treat the following as **RESOLVED** (verified against
`master`):

- **P2** — `--type venv` now matches `pyvenv.cfg` envs via `_TYPE_ALIASES`
  (`commands/_utils.py`); `doctor` filters detectors by *name*, so all
  `VenvDetector` envs are included. The underlying design (one detector emits
  two tags) stands but is fully handled. (P1 — no central `KNOWN_TYPES` — is
  still open.)
- **P6** — no detector sorts anymore; `Scanner.scan()` is the sole sort.
- **P9 / P10** — `clean.py` no longer calls `logging.basicConfig` (it has no
  logging at all); the pycache bypass is documented in
  `CODING_CONVENTIONS.md` §9.
- **P11** — `filter_envs` is defined once in `commands/_utils.py` and imported
  by both `list` and `delete` (no duplication).
- **P12** — `logging.basicConfig(level=logging.WARNING)` runs once in the
  `cli()` group in `__main__.py` (not in a subcommand). It was not wired to a
  `--verbose` flag.
- **P13** — `doctor._ENV_TYPES` is derived from `ALL_DETECTORS`
  (minus cache/artifacts), not hardcoded.
- **P3** — `can_handle()` no longer has three implicit, uncommented contracts.
  It is defined once in `AbstractDetector` and computed from declarative
  attributes (`required_tool` / `always_available` / `_candidate_dirs`); a test
  asserts every detector declares one. See `CODING_CONVENTIONS.md` §6.
- **P20 / §9** — `get_total_size` uses `os.walk` + `os.lstat` (symlink-safe) and
  catches `OSError`, not `rglob` / `FileNotFoundError`. `rglob` is used nowhere
  in the package.

Still open / deferred items are tracked in `CODING_CONVENTIONS.md` §22 (e.g. P1
type registry, subprocess timeouts, P4 eager sizing, P17 cli.py size).

______________________________________________________________________

## Table of Contents

1. [Dependency Graph](#1-dependency-graph)
1. [models.py — Core data contract](#2-modelspy--core-data-contract)
1. [detectors/ — Strategy layer](#3-detectors--strategy-layer)
1. [scanner.py — Orchestration layer](#4-scannerpy--orchestration-layer)
1. [cleaner.py vs cleaners/ — Naming collision](#5-cleanerpy-vs-cleaners--naming-collision)
1. [commands/ — CLI surface](#6-commands--cli-surface)
1. [intelligence/ — Scoring layer](#7-intelligence--scoring-layer)
1. [cli.py — TUI (TableApp)](#8-clipy--tui-tableapp)
1. [files/ — Size utilities](#9-files--size-utilities)
1. [Refactor Priority Summary](#10-refactor-priority-summary)

______________________________________________________________________

## 1. Dependency Graph

The dependency hierarchy is acyclic and well-structured. There are **no circular
imports**.

```
files/          ← pure utility, no internal imports
models.py       ← depends on files/
cleaners/       ← depends on files/
detectors/
  base.py       ← depends on models/
  *.py          ← depend on base, models, files/
scanner.py      ← depends on detectors/, models/
cleaner.py      ← depends on models/, subprocess
intelligence/
  git_analyzer  ← subprocess, filesystem
  scoring       ← depends on intelligence/git_analyzer, models/
  suggestions   ← depends on models/
  tracker       ← JSON, filesystem
commands/       ← depend on scanner, models, cleaner, intelligence/ (varies)
cli.py          ← TUI: depends on scanner, cleaner, commands, intelligence/
__main__.py     ← entry point: depends on everything
```

**Verdict:** Clean. The layering is respected throughout. The only coupling worth
watching is the `commands/` layer, where each command has a slightly different
relationship with `scanner` and `intelligence/`.

______________________________________________________________________

## 2. models.py — Core data contract

### Role

Defines every shared data shape in the project: `Environment`, `GitInfo`,
`ScoredEnvironment`, `Suggestion`, `ScanRecord`. All detectors produce
`Environment` instances; every command consumes them.

### What works well

- Single-file contract means the boundary between layers is obvious.
- `to_dict()` serialisation lives here, keeping JSON output consistent.
- `size_human` and `last_accessed_str` as `@property` avoids duplication in
  display code.

### Problems

**P1 — `type` is an uncontrolled string literal.**

The `type` field on `Environment` is a plain `str` with no central registry.
Each of the 11 detector files defines its own string in isolation:

```python
# venv.py
type=tag,          # "venv" or "pyvenv.cfg" — two values from ONE detector

# conda.py
type="conda",

# poetry.py
type="poetry",

# cache.py  (multiple possible values)
type=cache_type,   # "__pycache__", ".mypy_cache", ".pytest_cache", ...
```

Any code that filters by type (commands, tests) must know the exact strings.
A typo silently matches nothing and is invisible at runtime.

**P2 — VenvDetector emits two `type` values for the same logical detector.**

`VenvDetector.name = "venv"` but `detect()` returns environments tagged as
either `"venv"` or `"pyvenv.cfg"` depending on how the environment was found:

```python
# venv.py — two different tags from one detector
envs.append(_make_env(dir_path, ".venv"))   # type = ".venv"
envs.append(_make_env(venv_dir, "pyvenv.cfg"))  # type = "pyvenv.cfg"
```

When a user runs `killpy list --type venv`, they get results from the
`".venv"` branch but miss environments detected via `pyvenv.cfg`. The
`doctor` command's `_ENV_TYPES` set only includes `"venv"`, which means
`pyvenv.cfg`-tagged environments are excluded from doctor reports.

### Verdict

Mostly solid. The type-string problem is the most actionable issue.

### Refactor proposal

- **Option A (minimal):** Add a `KNOWN_TYPES` frozenset to `models.py` or
  `detectors/__init__.py` listing all canonical values. Mention it in
  `CODING_CONVENTIONS.md`. No code change needed now.
- **Option B (thorough):** Normalise VenvDetector to always emit `type="venv"`
  and store the original tag in a separate optional `subtype` field or use
  `name` for the display label. This is a breaking change for any code that
  filters by `type="pyvenv.cfg"`.

**Priority: Medium**

______________________________________________________________________

## 3. detectors/ — Strategy layer

### Role

11 detector classes, each responsible for discovering one kind of Python
environment. All implement the `AbstractDetector` interface: `name`, `detect()`,
`can_handle()`.

### What works well

- True Strategy pattern: the Scanner doesn't know anything about individual env
  types — it just calls `detect()` and aggregates.
- Each detector is self-contained and independently testable.
- `ALL_DETECTORS` in `detectors/__init__.py` is the single place to add/remove a
  detector.

### Problems

**P3 — `can_handle()` has three different implicit contracts.**

The base class docstring describes three possible behaviours, but does not
mandate which to use, so each detector implements its own interpretation with
no comment explaining why:

```python
# Type 1: check if external tool exists (conda.py, pipx.py)
def can_handle(self) -> bool:
    return shutil.which("conda") is not None

# Type 2: check if a directory exists (poetry.py, pyenv.py, pipenv.py, hatch.py)
def can_handle(self) -> bool:
    return _poetry_venvs_dir().exists()

# Type 3: always True (venv.py, tox.py, uv.py, cache.py, artifacts.py)
def can_handle(self) -> bool:
    return True
```

A reader (or agent) adding a new detector has no guidance on which variant to
choose.

**P4 — Eager size calculation on every detected environment.**

Every detector calls `get_total_size()` (a full recursive `rglob("*")`) for
each environment found before returning. This means all sizes are computed even
for environments the user will never act on:

```python
# conda.py (representative of all detectors)
size = get_total_size(env_path)   # full recursive walk here
envs.append(Environment(..., size_bytes=size, ...))
```

For large scans (hundreds of envs), this is the dominant performance cost. There
is no lazy evaluation or caching.

**P5 — Dual-layer deduplication, undocumented.**

`VenvDetector` maintains its own `seen: set[Path]` to avoid emitting the same
path from both the `.venv` scan and the `pyvenv.cfg` scan. `Scanner` then
deduplicates again across all detectors. This is correct but implicit — the
inner deduplication in `VenvDetector` is not documented, and a reader might
remove it thinking the Scanner handles it.

**P6 — Every detector sorts its own results.**

Every detector ends with:

```python
envs.sort(key=lambda e: e.size_bytes, reverse=True)
return envs
```

Then `Scanner.scan()` sorts the aggregated list again:

```python
results.sort(key=lambda e: e.size_bytes, reverse=True)
```

The per-detector sort is wasted O(n log n) work because the cross-detector
aggregation immediately breaks the sorted order.

### Verdict

The pattern is clean and well-implemented. Problems P4 and P6 are performance
issues that don't affect correctness. P3 is a documentation gap. P5 is a
correctness risk if the code is edited without understanding the intent.

### Refactor proposals

- **P3:** Document the three variants in `AbstractDetector.can_handle()`.
  Each concrete implementation should add a one-line comment stating which
  variant it uses (e.g., `# Type: always True — pure filesystem scan`).
- **P4 (future):** Make `size_bytes` lazy (computed on first access) or accept
  a `compute_sizes: bool = True` flag in `Scanner.scan()`.
- **P5:** Add a comment in `VenvDetector.detect()` explaining the local `seen`
  set and why it coexists with Scanner's deduplication.
- **P6:** Remove per-detector sorts. Sorting is the Scanner's responsibility.

**Priority: Low (P3, P5, P6) / Medium (P4 if performance becomes a concern)**

______________________________________________________________________

## 4. scanner.py — Orchestration layer

### Role

Instantiates all detectors, calls `detect()` on each, deduplicates across
detectors, calls an optional `on_progress` callback, and returns a size-sorted
list. The async variant (`scan_async`) yields results progressively for the TUI.

### What works well

- Clean separation from detection logic.
- Deduplication via `path.resolve()` handles symlinks correctly.
- `types` and `excluded` filters let commands use a subset of detectors without
  code changes.
- The `on_progress` callback pattern is simple and doesn't require the scanner
  to know about the UI.

### Problems

**P7 — `scan_async` result order is non-deterministic.**

`scan_async` uses `asyncio.as_completed`, meaning results arrive in the order
detectors finish, not the order of `ALL_DETECTORS`. The TUI appends rows as
they arrive, so the table can appear in different orders on each run:

```python
tasks = [asyncio.create_task(_run(d)) for d in applicable]
for coro in asyncio.as_completed(tasks):   # ← non-deterministic order
    detector, found = await coro
    yield detector, deduped
```

This is by design (responsiveness), but there is no documentation stating this.
A reader might assume results arrive in `ALL_DETECTORS` order.

**P8 — `_mark_system_critical` uses `sys.prefix` as a proxy for "active env".**

This is correct for the current interpreter, but if killpy is installed
globally (e.g., via pipx), `sys.prefix` points to the pipx venv, not the
project venvs the user might want to delete. The logic is correct for the
common case but can produce false positives.

### Verdict

Well-designed. The only actionable issue is adding a docstring note about the
non-deterministic ordering of `scan_async`.

**Priority: Low**

______________________________________________________________________

## 5. cleaner.py vs cleaners/ — Naming collision

### Role

- `cleaner.py`: `Cleaner` class — stateful (has `dry_run`), dispatches
  deletion to `shutil.rmtree`, `conda env remove`, or `pipx uninstall`.
- `cleaners/__init__.py`: `remove_pycache()` — stateless module-level
  function, walks directory recursively and removes `__pycache__` dirs.

### What works well

- `Cleaner` is a clean adapter: callers never need to know whether deletion
  is a filesystem op or a subprocess call — they always call `cleaner.delete(env)`.
- `CleanerError` provides a typed exception boundary.

### Problems

**P9 — The two modules have deceptively similar names but structurally different APIs.**

`cleaner.py` = stateful class with `dry_run` support and `CleanerError`
propagation.
`cleaners/` = stateless function with no `dry_run`, no `CleanerError`, silent
on exceptions (`except Exception: continue`).

```python
# cleaner.py — dry_run respected, CleanerError raised
def delete(self, env: Environment) -> int:
    if self.dry_run:
        logger.info("[dry-run] Would delete %s", env.path)
        return env.size_bytes
    ...
    shutil.rmtree(env.path)

# cleaners/__init__.py — no dry_run, silently continues on error
def remove_pycache(path: Path) -> int:
    for pycache_dir in path.rglob("__pycache__"):
        try:
            shutil.rmtree(pycache_dir)
        except Exception:
            continue   # ← no logging, no dry_run
```

`clean` command also calls `logging.basicConfig()` inside the command handler,
while `delete` does not — creating an asymmetry in log visibility.

**P10 — `remove_pycache` bypasses the `Cleaner` abstraction entirely.**

The `clean` command never uses `Scanner` or `Cleaner`. It calls
`remove_pycache()` directly. This means pycache removal has no dry-run support
and no unified deletion tracking (history is not updated).

```python
# commands/clean.py — bypasses Scanner and Cleaner
def clean(path):
    logging.basicConfig(level=logging.INFO)
    total_freed_space = remove_pycache(path)   # direct call, no dry_run
```

### Verdict

**This is the most structurally confusing part of the codebase.** The naming
implies symmetry (`cleaner` / `cleaners`) but the two are architecturally
different. The bypass in `clean` is intentional but undocumented.

### Refactor proposals (choose one)

- **Option A (rename):** Rename `cleaners/` to `pycache/` (or move
  `remove_pycache` into `cleaners/pycache.py`). This breaks the visual
  association between `cleaner.py` and `cleaners/`.
- **Option B (unify):** Add `Cleaner.clean_pycache(path, dry_run)` method so
  that all deletion goes through the same entry point. The `cleaners/` module
  becomes an internal helper.

**Priority: Medium**

______________________________________________________________________

## 6. commands/ — CLI surface

### Role

5 subcommands: `clean`, `list`, `delete`, `stats`, `doctor`. Each is a
`@click.command` function registered in `__main__.py`.

### What works well

- Commands are thin: they parse args, delegate to `Scanner` + `Cleaner` +
  `intelligence/`, and format output.
- `list` and `delete` share a `_filter_envs` helper defined locally in each
  file. They are near-identical.

### Problems

**P11 — `_filter_envs` is duplicated between list.py and delete.py.**

```python
# list.py
def _filter_envs(envs, types, older_than): ...

# delete.py
def _filter_envs(envs, types, older_than): ...  # identical logic
```

If a filter bug is fixed in one, it will silently persist in the other.

**P12 — Logging is only configured in `clean.py`.**

`clean.py` calls `logging.basicConfig(level=logging.INFO)` inside the command
handler. All other commands never call `basicConfig`, meaning logging output
from other commands is suppressed unless the user has configured the root
logger externally (e.g., via a `logging.ini` or PYTHONWARNINGS):

```python
# commands/clean.py — only command that configures logging
def clean(path):
    logging.basicConfig(level=logging.INFO)
    ...
```

This is also stylistically wrong: `basicConfig` should be called at application
startup (`__main__.py`), not inside a command handler.

**P13 — `doctor` hardcodes `_ENV_TYPES` instead of deriving from `ALL_DETECTORS`.**

```python
# commands/doctor.py
_ENV_TYPES: set[str] = {
    "venv", "poetry", "conda", "pipx", "pyenv",
    "pipenv", "hatch", "uv", "tox",
}
```

When a new detector is added to `ALL_DETECTORS`, `doctor` will silently miss it
unless `_ENV_TYPES` is manually updated. There is no test that catches drift.

### Verdict

The commands layer is mostly clean. P11, P12, and P13 are low-effort fixes
with meaningful correctness and maintenance impact.

### Refactor proposals

- **P11:** Move `_filter_envs` to a shared `commands/_filters.py` module (or
  directly into `models.py` as `Environment.matches_filters()`).
- **P12:** Call `logging.basicConfig()` once in `__main__.py`'s `cli()` group,
  controlled by a `--verbose` flag. Remove the call from `clean.py`.
- **P13:** Either compute `_ENV_TYPES` from `ALL_DETECTORS` dynamically, or
  add a test that asserts `_ENV_TYPES` is a subset of known detector names.

**Priority: Medium (P11, P12) / Low (P13)**

______________________________________________________________________

## 7. intelligence/ — Scoring layer

### Role

Four modules: `git_analyzer.py` (git repo detection), `scoring.py` (deletion
priority scoring via weighted factors), `suggestions.py` (HIGH/MEDIUM/LOW
classification), `tracker.py` (scan history persistence).

### What works well

- Well-designed internally. Each module has a clear single responsibility.
- `ScoredEnvironment` wraps `Environment` via composition, so the plain
  `Environment` contract is never broken.
- `UsageTracker` uses atomic writes (temp file → rename) for history, avoiding
  data corruption on crash.
- All I/O in `tracker.py` is best-effort (failures are swallowed, not fatal).

### Problems

**P14 — The intelligence layer is siloed to `doctor` and `stats`.**

`list` and `delete` do not use scoring. A user running `killpy list` sees no
score or suggestion; `killpy delete --type venv` deletes all venvs regardless
of whether they are orphaned or active. This is not a bug but a design gap —
the richer data model was added but not wired to the most-used commands.

**P15 — `doctor` uses `_ENV_TYPES` (see P13) which could drift from scoring.**

`SuggestionEngine` and `ScoringService` operate on whatever environments they
receive. If `_ENV_TYPES` in `doctor.py` drifts from the real detector names,
the scoring results will be silently incomplete.

**P16 — `ScoredEnvironment` wraps `Environment` loosely.**

`ScoredEnvironment.env` is the inner environment, but many callers access
`scored.env.path` rather than having a shortcut. This is minor but adds
verbosity throughout `suggestions.py` and `scoring.py`.

### Verdict

Solid internal design. The main gap is integration with other commands, which
is a product decision rather than a structural defect.

**Priority: Low (integration gap is a feature decision) / Medium (P13/P15 coupling risk)**

______________________________________________________________________

## 8. cli.py — TUI (TableApp)

### Role

Textual `App` subclass. Renders two `DataTable` widgets (venvs, pipx packages),
starts a background async scan via `scanner.scan_async()`, handles keyboard
shortcuts for marking and deleting environments.

### What works well

- Non-blocking startup: the app renders immediately, then appends rows as
  detectors finish.
- The `scan_async` → `on_progress` → `call_from_thread` pattern is the correct
  Textual idiom for background work.
- `is_system_critical` flag visually highlights the active interpreter venv.

### Problems

**P17 — Large file mixing layout, event handling, async orchestration, and deletion.**

`cli.py` has grown to handle UI construction, keyboard bindings, async scanning,
confirmation prompts, and `Cleaner` calls in one class. This is typical for TUI
code but makes individual functions hard to test in isolation.

**P18 — `VenvRow` / `PipxRow` TypedDicts vs the AGENTS.md tuple documentation.**

`AGENTS.md` documents the row contract as tuples:

```
Venv-like rows are expected as tuples:
  (path, type, last_modified, size_bytes, size_human)
```

But `cli.py` uses `TypedDict` internally. The two are not directly related —
`TypedDict` is only used for type checking, not at runtime — but the
documentation is misleading for contributors.

### Verdict

Acceptable for a TUI file of this complexity. The main action item is updating
AGENTS.md to reflect the TypedDict approach rather than bare tuples.

**Priority: Low**

______________________________________________________________________

## 9. files/ — Size utilities

### Role

Two pure functions: `get_total_size(path)` (recursive byte sum) and
`format_size(size_bytes)` (human-readable string).

### What works well

- Single source of truth for size calculation and formatting.
- `format_size` covers GB, MB, KB, and bytes.
- `get_total_size` catches `OSError` per entry during traversal to handle
  race conditions (files deleted mid-scan) and does not follow symlinks.

### Problems

**P19 — `format_size` uses bit-shift comparisons.**

```python
if size_bytes >= 1 << 30:    # 1 GB
    return f"{size_bytes / (1 << 30):.2f} GB"
elif size_bytes >= 1 << 20:  # 1 MB
    ...
```

Bit-shifts are correct (`1 << 30 = 1 073 741 824`) but non-obvious. The inline
comments help but a contributor unfamiliar with this idiom may be confused. Using
named constants (`_GB = 1 << 30`) would be clearer.

**P20 — `get_total_size` uses `rglob("*")` without directory pruning.**

Unlike the detectors which use `os.walk(..., topdown=True)` with pruning,
`get_total_size` calls `path.rglob("*")` which cannot prune subtrees. For
environments that contain deeply nested virtual environments inside virtual
environments, this can be slower than necessary. In practice this is not a
problem because size is computed on finalised env paths.

### Verdict

Solid. Minor style and performance notes, no structural issues.

**Priority: Low**

______________________________________________________________________

## 10. Refactor Priority Summary

| # | Issue | Module(s) | Priority | Effort |
|---|-------|-----------|----------|--------|
| P9/P10 | `cleaner.py` vs `cleaners/` naming + `clean` bypass | `cleaner.py`, `cleaners/`, `commands/clean.py` | **Medium** | Small |
| P11 | `_filter_envs` duplicated in `list.py` and `delete.py` | `commands/list.py`, `commands/delete.py` | **Medium** | Small |
| P12 | `logging.basicConfig` only in `clean.py` | `commands/clean.py`, `__main__.py` | **Medium** | Small |
| P1/P2 | `type` string literals uncontrolled, VenvDetector emits 2 types | `models.py`, `detectors/venv.py` | **Medium** | Small–Medium |
| P13 | `doctor._ENV_TYPES` can drift from `ALL_DETECTORS` | `commands/doctor.py` | **Low** | Trivial |
| P3 | `can_handle()` semantics undocumented | `detectors/base.py`, all detectors | **Low** | Trivial |
| P5 | VenvDetector inner `seen` set undocumented | `detectors/venv.py` | **Low** | Trivial |
| P6 | Per-detector sort wasted | All detectors | **Low** | Small |
| P4 | Eager size calculation | All detectors | **Low** | Medium |
| P7 | `scan_async` non-deterministic order undocumented | `scanner.py` | **Low** | Trivial |
| P14 | `intelligence/` not used by `list` / `delete` | `commands/list.py`, `commands/delete.py` | **Low** | Large |
| P17 | `cli.py` mixes concerns | `cli.py` | **Low** | Large |
| P18 | AGENTS.md tuple docs vs TypedDict reality | `AGENTS.md`, `cli.py` | **Low** | Trivial |
| P19 | Bit-shift magic in `format_size` | `files/__init__.py` | **Low** | Trivial |

### Recommended order of attack

1. Fix the `cleaners/` naming and `clean` bypass (P9/P10) — highest
   confusion-to-effort ratio.
1. Deduplicate `_filter_envs` (P11) and centralise `logging.basicConfig` (P12).
1. Add a `KNOWN_TYPES` constant to kill the string-literal problem at its root
   (P1/P2, P13).
1. Remove per-detector sorts (P6) — mechanical, zero risk.
1. Document `can_handle()` variants (P3) and `VenvDetector` inner dedup (P5) —
   purely additive comments.
