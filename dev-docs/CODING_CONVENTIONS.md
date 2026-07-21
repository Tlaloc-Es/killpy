# killpy — Coding Conventions

> **Audience:** Developers and coding agents about to write or modify code in this project.
> **Purpose:** Eliminate ambiguity. When there is more than one way to do something in
> this codebase, this document declares which way is correct and why.
> **Last reviewed:** July 2026 — reconciled against the `master` branch during a
> full consistency audit. Every rule below was verified against the code as it
> actually is, not as it was once intended to be.

This is NOT user documentation. It is an internal reference. Each rule is derived
from patterns present in the code today. Where the code is inconsistent, the rule
states the winning convention and flags the outliers.

______________________________________________________________________

## Table of Contents

1. [Module layout: docstring + `from __future__ import annotations`](#1-module-layout)
1. [Naming conventions](#2-naming-conventions)
1. [Directory traversal and size calculation](#3-directory-traversal-and-size-calculation)
1. [Shared directory-name constants](#4-shared-directory-name-constants)
1. [Detector contract](#5-detector-contract)
1. [`can_handle()`: the four contracts](#6-can_handle-the-four-contracts)
1. [Environment `type` strings and `--type` filtering](#7-environment-type-strings)
1. [Sorting is the Scanner's job](#8-sorting-is-the-scanners-job)
1. [Scanner vs. calling a detector directly](#9-scanner-vs-detector)
1. [Deletion routing: `managed_by`, not `type`](#10-deletion-routing)
1. [Deletion safety guards](#11-deletion-safety-guards)
1. [Exception handling by layer](#12-exception-handling-by-layer)
1. [`subprocess.run` conventions](#13-subprocessrun-conventions)
1. [Logging](#14-logging)
1. [Path construction and resolution](#15-path-construction-and-resolution)
1. [Data models, serialization, and validation](#16-data-models)
1. [Size formatting: `format_size` / `size_human`](#17-size-formatting)
1. [Atomic writes for persistent state](#18-atomic-writes)
1. [CLI command structure](#19-cli-command-structure)
1. [Tests](#20-tests)
1. [Automatically enforced rules](#21-automatically-enforced-rules)
1. [Known deviations and deferred decisions](#22-known-deviations)

______________________________________________________________________

## 1. Module layout

Every non-empty module opens with a one-line module docstring immediately
followed by `from __future__ import annotations`, then the import block:

```python
"""Detector for local ``.venv`` directories and ``pyvenv.cfg`` files."""

from __future__ import annotations

import logging
import os
...
```

- The docstring is mandatory and describes what the module *is*.
- `from __future__ import annotations` is mandatory in every module that has any
  annotations. It keeps annotations lazy so `X | None` / `list[X]` never cost
  anything at runtime and stay valid on the 3.10 floor.
- Empty package markers (`killpy/__init__.py`, `killpy/commands/__init__.py`) are
  intentionally 0 bytes and carry neither.

Import ordering is handled by ruff (`I`); do not hand-order imports.

______________________________________________________________________

## 2. Naming conventions

| Kind | Rule | Examples |
|---|---|---|
| Module files | lower_snake, one concept per file | `git_analyzer.py`, `_utils.py` |
| Classes | `PascalCase` with a role suffix | `VenvDetector`, `Scanner`, `Cleaner`, `ScoringService`, `SuggestionEngine`, `GitAnalyzer`, `UsageTracker`, `TableApp` |
| click callbacks | `<verb>_cmd`, with an explicit command name in the decorator | `def delete_cmd(...)` under `@click.command("delete")` |
| Module-private helpers | leading underscore | `_make_env`, `_pyenv_root`, `_looks_like_path`, `_summarise` |
| Public module functions | no underscore, and genuinely imported elsewhere | `format_size`, `get_total_size`, `filter_envs`, `remove_pycache` |
| Module-level constants | `_LEADING_UNDERSCORE_UPPER` when private, `UPPER` when exported | `_ACTIVE_THRESHOLD_DAYS`, `_TYPE_ALIASES`; exported: `VCS_PRUNE_DIRS`, `ENV_INTERNAL_DIRS`, `ALL_DETECTORS` |
| A byte count | always spelled `size_bytes` | `Environment.size_bytes`, `format_size(size_bytes)`, `record_deletion(size_bytes)` |
| A filesystem path parameter | `path`, or a descriptive `*_path` / `*_dir` | `cache_path`, `venv_path`, `env_dir`, `repo_root` |

Anti-patterns to avoid (all removed during the audit):

```python
# WRONG — click callback without _cmd suffix or explicit name
@click.command()
def clean(path): ...

# WRONG — single-letter path parameter where peers use a descriptive name
def _make_cache_env(p: Path, tag: str) -> Environment: ...

# WRONG — public name for a module-internal helper
def shorten_path_for_table(...):   # used only inside cli.py → should be _shorten_path_for_table
```

______________________________________________________________________

## 3. Directory traversal and size calculation

**All filesystem traversal uses `os.walk(..., topdown=True)`. `Path.rglob()` is
used nowhere in the package** and must not be reintroduced.

Walking a project tree — prune irrelevant subtrees in place so they are never
descended into:

```python
for current_root, directories, files in os.walk(root, topdown=True):
    directories[:] = [d for d in directories if d not in _EXCLUDED_DIRS]
    ...
```

Computing a directory's size — `get_total_size` walks with `os.walk` and sums
`os.lstat(...).st_size`. It uses `lstat`, never `stat`, so **symlinks are never
followed**: a link inside an environment cannot pull in the size of targets
outside it or create walk loops. Per-entry `OSError` is swallowed (files can
vanish mid-scan):

```python
def get_total_size(path: Path) -> int:
    total_size = 0
    for current_root, _dirs, files in os.walk(path):
        for name in files:
            try:
                total_size += os.lstat(os.path.join(current_root, name)).st_size
            except OSError:
                continue
    return total_size
```

`remove_pycache` follows the same rule: `os.walk` + prune the matched dir + skip
symlinked `__pycache__` targets.

______________________________________________________________________

## 4. Shared directory-name constants

The directory-name sets used while walking live in **one** place —
`killpy/detectors/base.py` — and are imported by the detectors that need them:

```python
# base.py
VCS_PRUNE_DIRS: frozenset[str] = frozenset({".git", ".hg", ".svn", "node_modules"})
ENV_INTERNAL_DIRS: frozenset[str] = frozenset({".venv", "site-packages"})
```

- `VCS_PRUNE_DIRS` — never descended into (tox, cache, artifacts, and venv all use it).
- `ENV_INTERNAL_DIRS` — an environment's own internals; cache/artifact detectors
  skip these so they don't double-count or offer to delete env contents.
- `VenvDetector._EXCLUDED_DIRS` is a deliberately *wider* superset built as
  `VCS_PRUNE_DIRS | {…cache/build dirs…}` — but it must **not** include
  `.venv`/`site-packages`, because that is exactly what it is searching for.

Do not copy these literals into individual detectors. If you add a new prune
target (e.g. `.jj`), add it to the shared constant once.

______________________________________________________________________

## 5. Detector contract

> Adding a whole new detector? Follow the step-by-step guide in
> [`ADDING_A_DETECTOR.md`](ADDING_A_DETECTOR.md); this section is the rule
> reference it builds on.

Every concrete detector subclasses `AbstractDetector` and:

- Defines a unique `name` class attribute (used for logging, `--type` filtering,
  and Scanner selection).
- Implements `detect(self, path: Path) -> list[Environment]` returning a **`list`,
  never a generator** (the Scanner deduplicates and the async path runs
  `detect` in a thread via `asyncio.to_thread`, both of which need a complete,
  reusable result).
- Declares its `can_handle()` contract as data — never overrides `can_handle()`
  itself (see §6).
- **Must not raise** from `detect()` — on error, log and return what was found
  so far (or `[]`). See §12.
- **Must not sort** its results (see §8).
- Ignores the `path` argument when it scans a fixed global location (conda,
  poetry, pyenv, pipenv, hatch, uv, pipx). Mark that parameter
  `def detect(self, path: Path) -> list[Environment]:  # noqa: ARG002`.

`VenvDetector` keeps a local `seen: set[Path]` because its `.venv` scan and its
`pyvenv.cfg` scan can reach the same directory. This coexists intentionally with
the Scanner's cross-detector dedup — the comment in `venv.py` documents why;
do not remove it.

______________________________________________________________________

## 6. `can_handle()`: the four contracts

`can_handle()` is a cheap pre-flight gate: it returns `False` only when it is
*impossible* for this detector to find anything on the current system. It must
never raise and must do no I/O beyond a `which()` and/or an `exists()` check.

**`can_handle()` is defined once, in `AbstractDetector`, and is never overridden.**
Each detector instead *declares* its contract as data, and the base computes the
result — so the declared contract and the runtime behaviour cannot diverge, and a
mistyped/forgotten contract is caught by a test rather than living silently in a
comment.

There are **four** contracts, expressed by which of three things a detector
declares:

| Contract | Declared via | Example detectors |
|---|---|---|
| `always True` | `always_available = True` | venv, tox, cache, artifacts |
| `tool` | `required_tool = "<cli>"` | conda, pipx |
| `directory` | override `_candidate_dirs()` | poetry, pyenv |
| `tool-or-directory` | `required_tool` **and** `_candidate_dirs()` | pipenv, hatch, uv |

```python
# base.py — the single implementation
def can_handle(self) -> bool:
    if self.always_available:
        return True
    if self.required_tool is not None and shutil.which(self.required_tool):
        return True
    return any(d.exists() for d in self._candidate_dirs())

# uv.py — declaration only, no can_handle()
class UvDetector(AbstractDetector):
    name = "uv"
    required_tool = "uv"                       # tool-or-directory contract

    def _candidate_dirs(self) -> tuple[Path, ...]:
        return (_uv_tools_dir(), _uv_python_dir())
```

`_candidate_dirs()` is a method (not a class attribute holding function
references) on purpose: it calls the path helpers at *runtime*, so a test that
patches `killpy.detectors.<x>._<x>_dir` is honoured (a captured reference would
not be). `tests/unit/test_detectors.py::TestDetectorContract` asserts every
detector in `ALL_DETECTORS` declares at least one of the three — so a new
detector that declares nothing (and would silently never run) fails CI.

______________________________________________________________________

## 7. Environment `type` strings

`Environment.type` is a plain lowercase string. Each detector sets it to a
literal (there is no central enum):

- Single-type detectors emit their own tag: `type="conda"`, `"poetry"`,
  `"pyenv"`, `"pipenv"`, `"hatch"`, `"uv"`, `"tox"`, `"artifacts"`.
- `VenvDetector` emits **`".venv"`** or **`"pyvenv.cfg"`** (not `"venv"`).
- `CacheDetector` emits one of `"__pycache__"`, `".mypy_cache"`,
  `".pytest_cache"`, `".ruff_cache"`, `"pip-cache"`, `"uv-cache"`.

Because the emitted tags differ from the user-facing detector *name*, the
**single source of truth for `--type` expansion is `_TYPE_ALIASES` in
`commands/_utils.py`**. `filter_envs` expands a requested name (`venv`, `cache`)
to its concrete tags. When you add a detector that emits tags different from its
`name`, update `_TYPE_ALIASES` — otherwise `--type <name>` silently matches
nothing.

> A central `KNOWN_TYPES` registry would make this safer; it is a deferred
> decision (see §22), not a rule.

______________________________________________________________________

## 8. Sorting is the Scanner's job

Detectors return results in discovery order. **No detector sorts** (verified:
`grep -r '\.sort(' killpy/detectors/` is empty). `Scanner.scan()` performs the
single size-sort at the end:

```python
results.sort(key=lambda e: e.size_bytes, reverse=True)
return results
```

Note `scan_async` yields per-detector as each finishes (`asyncio.as_completed`),
so its cross-detector order is intentionally non-deterministic — the TUI sorts
its own view. Don't rely on `scan_async` yielding in `ALL_DETECTORS` order.

______________________________________________________________________

## 9. Scanner vs. detector

All user-facing commands enumerate environments through `Scanner`, never by
instantiating a detector directly. `Scanner` provides deduplication, exclusion
filtering, and system-critical flagging for free.

```python
scanner = Scanner(types=set(types) if types else None)
envs = scanner.scan(path)
```

The one intentional exception is `killpy clean`, which calls `remove_pycache()`
directly (a bulk best-effort cache wipe that never needs the `Environment`
model). Do not replicate that bypass in new commands.

______________________________________________________________________

## 10. Deletion routing

`Cleaner.delete()` chooses its removal strategy from `Environment.managed_by`,
never from `type`:

```python
if env.managed_by == "conda":   self._remove_conda(env.name)
elif env.managed_by == "pipx":  self._remove_pipx(env.name)
elif env.managed_by == "uv":    self._remove_uv_tool(env.name)
elif not self._remove_filesystem(env.path): return 0
```

`type` describes what an environment *is*; `managed_by` describes *how to remove
it*. The supported `managed_by` values are `"conda"`, `"pipx"`, `"uv"`, or
`None` (filesystem removal).

______________________________________________________________________

## 11. Deletion safety guards

Filesystem removal goes through `Cleaner._ensure_sane_deletion_target()` before
any `shutil.rmtree`. These checks are unconditional — **`force` does not bypass
them** — and are defense-in-depth against a bug upstream or a directory swapped
between scan and delete:

- Refuse a target that `is_symlink()`.
- Refuse the filesystem root and `Path.home()`.
- Refuse a target fewer than `_MIN_DEPTH_BELOW_ROOT` (2) components below the
  anchor (e.g. `/usr`, `/home/x`).

`force` only overrides the separate `is_system_critical` refusal. New deletion
paths must route through `Cleaner`, not call `shutil.rmtree` directly, so these
guards always apply.

______________________________________________________________________

## 12. Exception handling by layer

| Context | Pattern |
|---|---|
| Detector `detect()`, file/path helpers | Catch the specific expected errors: `(FileNotFoundError, OSError)`, plus `subprocess.CalledProcessError` / `json.JSONDecodeError` when relevant. Log at DEBUG, continue or return `[]`. **Never** `except Exception` here. |
| Scanner / orchestration | `except Exception as exc:  # noqa: BLE001` — one detector's failure must not abort the scan. Log at WARNING and continue. |
| Best-effort fire-and-forget (history tracking) | `except Exception:  # noqa: BLE001` then `pass` — a failure here is irrelevant to the user. |
| Best-effort cleanup loops (`remove_pycache`) | Narrow `except OSError: continue` — the only failure mode is a filesystem error. |
| `Cleaner` | Wrap the underlying failure in a typed `CleanerError`; re-raise `CleanerError` unchanged (`except CleanerError: raise`). |

The `# noqa: BLE001` marker is required on every intentional broad catch even
though `BLE` is not in the active ruff rule set — it documents that the breadth
is deliberate. (`cleaners/__init__.py` uses a narrow `OSError` catch and
therefore needs no marker.)

```python
# CORRECT — detector: specific catch, DEBUG log, return []
except (FileNotFoundError, OSError) as exc:
    logger.debug("Skipping %s: %s", dir_path, exc)

# CORRECT — orchestration: broad catch, documented, WARNING log
except Exception as exc:  # noqa: BLE001
    logger.warning("Detector %s raised: %s", detector.name, exc)
    found = []
```

______________________________________________________________________

## 13. `subprocess.run` conventions

Every `subprocess.run` call passes `capture_output=True, text=True`. Beyond
that, two idioms are permitted by context:

**A. Read-only enumeration** where any failure means "nothing to report"
(`conda env list`, `pipx list --json`): use `check=True` and catch the tool's
failure modes, returning `[]`.

```python
try:
    result = subprocess.run(
        ["conda", "env", "list"], capture_output=True, text=True, check=True,
    )
except FileNotFoundError:
    return []
except subprocess.CalledProcessError as exc:
    logger.debug("conda env list failed: %s", exc)
    return []
except OSError as exc:
    logger.debug("OS error running conda: %s", exc)
    return []
```

**B. Calls that inspect output/returncode manually, or surface a typed error**
(`git log`, and the `Cleaner` removals): use `check=False` and check
`returncode` explicitly.

```python
result = subprocess.run([...], check=False, capture_output=True, text=True, timeout=10)
if result.returncode != 0:
    ...  # return None / raise CleanerError
```

**Timeout:** `git_analyzer` passes `timeout=10` (a huge repo's `git log` could
otherwise hang) and catches `subprocess.TimeoutExpired`. The read-only
enumeration calls and the `Cleaner` removals currently pass no timeout — see
§22: adding one is a *behavior* change (a destructive `conda env remove` on a
large env must be allowed to finish), so it is deferred, not silently applied.

______________________________________________________________________

## 14. Logging

- Every module creates its logger with `logger = logging.getLogger(__name__)`
  and nothing else.
- **Module code never calls `logging.basicConfig()`, `setLevel()`, or
  `addHandler()`.** Logging is configured exactly once, at application startup,
  in the `cli()` group in `__main__.py`: `logging.basicConfig(level=logging.WARNING)`.
- User-facing output uses `click.echo()` (for machine-readable/stdout, e.g.
  JSON) or a `rich` `Console` (for styled terminal output) — **not** `logger`.
- `logger.*` is for diagnostics only.

Level guide:

| Level | When |
|---|---|
| `DEBUG` | detector skipped, parser edge cases, per-item `OSError`, an inaccessible entry inside a scan |
| `INFO` | a deletion completed (what/how much) |
| `WARNING` | a detector raised; a path is inaccessible but the scan continues |
| `ERROR` | data corruption (invalid JSON in history), an unrecoverable non-fatal path |

______________________________________________________________________

## 15. Path construction and resolution

Use `pathlib.Path` for all path work; never `os.path.join`, `os.path.exists`,
or string concatenation (the one `os.path.join` inside `get_total_size` is a
deliberate hot-loop micro-optimisation over already-split `os.walk` output).

Dedup by resolved path, with a fallback to the unresolved path on `OSError`:

```python
try:
    resolved = env.path.resolve()
except OSError:
    resolved = env.path
```

Use `resolve(strict=True)` only inside detector code, where you are verifying an
environment exists at the moment of detection. Never use `strict=True` in the
Scanner — paths may vanish between scan and dedup.

______________________________________________________________________

## 16. Data models

All shared shapes are dataclasses in `models.py`: `Environment`, `GitInfo`,
`ScoredEnvironment`, `Suggestion`, `ScanRecord`.

- **Serialization belongs to the model.** A dataclass that is emitted as JSON
  owns a `to_dict()` (`Environment`, `Suggestion`, `ScanRecord`). Commands must
  call `x.to_dict()`, not hand-assemble the dict. Add `from_dict()` only where a
  model is read back from disk (currently only `ScanRecord`).
- Closed-set string fields use `typing.Literal`: `Suggestion.category` is
  `Literal["HIGH", "MEDIUM", "LOW"]`. `Environment.type` and
  `Environment.managed_by` are open `str` / `str | None` (many/extensible values).
- Computed display values are `@property` (`size_human`, `last_modified_str`),
  never duplicated in callers.
- Construct `Environment` directly in each detector. Two filesystem detectors
  use a local `_make_env` / `_make_cache_env` factory; that is a per-module
  convenience, not a required shared helper.
- The `name` field is NOT uniform by design: filesystem-walk detectors store the
  full path string; global/tool detectors store a short identifier. This is
  documented on the field and intentional (see §22).

______________________________________________________________________

## 17. Size formatting

`killpy.files.format_size(size_bytes: int) -> str` is the only size formatter.
Never format sizes inline.

```python
print(format_size(env.size_bytes))   # for a raw int
print(env.size_human)                # preferred when you hold an Environment
```

`format_size` uses bit-shift thresholds (`1 << 30` = 1 GB, `1 << 20` = 1 MB,
`1 << 10` = 1 KB). This is intentional and correct; keep the inline `# 1 GB`
style comments if you touch it.

______________________________________________________________________

## 18. Atomic writes for persistent state

Persistent files (scan history) are written atomically: write to a unique temp
file in the same directory, then `os.replace()` into place (atomic on the same
filesystem). Clean up the temp file if the write fails.

```python
# tracker.py
fd, tmp = tempfile.mkstemp(dir=self._path.parent, prefix=".history_", suffix=".json")
try:
    with os.fdopen(fd, "w", encoding="utf-8") as fh:
        json.dump(history, fh, indent=2, default=str)
    os.replace(tmp, self._path)
except Exception:
    try:
        os.unlink(tmp)
    except OSError:
        pass
    raise
```

Use `tempfile.mkstemp` (unique name, no clobber), not a fixed `.tmp` sibling.
Use `os.replace`, not `Path.rename`. The whole history layer is best-effort: the
outer wrapper swallows `OSError` at DEBUG so a write failure never reaches the
user.

______________________________________________________________________

## 19. CLI command structure

Each subcommand is a thin `@click.command("<name>")` in `commands/<name>.py`,
registered in `__main__.py` via `cli.add_command(<name>_cmd, name="<name>")`.

Shared option spelling (use these exact names for these concepts):

| Concept | Option |
|---|---|
| scan root | `--path` (defaults to `Path.cwd`) |
| type filter | `--type` (repeatable, dest `types`) |
| age filter | `--older-than DAYS` |
| JSON output | `--json` (dest `as_json`); `list` also has `--json-stream` |
| skip confirmation | `--yes` / `-y` |
| include in-use envs | `--force` |
| preview only | `--dry-run` |

Output mechanism: JSON goes through `click.echo(json.dumps(...))` (clean
stdout); human tables/messages go through a `rich` `Console`. Share filtering
via `commands/_utils.filter_envs` and in-use handling via
`commands/_utils.partition_in_use` — do not re-implement them per command.

> JSON key divergence between commands (`stats` → `total_count`, `doctor` →
> `total_environments`) and the two "delete everything" flows (root
> `--delete-all` vs `delete`) are known and NOT changed here because they are
> observable-contract changes — see §22.

______________________________________________________________________

## 20. Tests

- **Mock objects** (detectors/cleaners/scanners): factory functions named
  `_stub_<thing>()` / `_make_<thing>()`, typically `MagicMock(spec=AbstractDetector)`.
- **Data model instances** (`Environment`, `ScoredEnvironment`, `GitInfo`):
  construct directly — they are pure dataclasses.
- **Filesystem fixtures**: `tmp_path`-based helpers named `_make_venv()`,
  `_make_pycache()`, etc. at the top of the test module.
- Subprocess is always mocked (`patch("subprocess.run")`); tests never spawn a
  real process. When a detector uses `check=True`, its failure test drives
  `side_effect=subprocess.CalledProcessError(...)`; a `check=False` caller's
  failure test sets `return_value=MagicMock(returncode=1, ...)`.

______________________________________________________________________

## 21. Automatically enforced rules

`ruff` (config in `.ruff.toml`) enforces, and CI runs, the mechanical rules —
do not fight them by hand:

- Line length 88, double quotes, space indent, magic trailing comma.
- Import sorting (`I`), pyflakes (`F`), pycodestyle (`E`/`W`), naming (`N`),
  pyupgrade (`UP`), complexity (`C90`, max 10), and a subset of pylint
  (`PL*`, `max-args = 6`).
- `tests/**` may use magic numbers (`PLR2004` ignored there).

Commands (`pyproject.toml` `[tool.poe.tasks]`):

```
poe lint    # ruff check killpy tests
poe format  # ruff format killpy tests
poe type    # mypy killpy
poe test    # pytest (with coverage)
```

The `can_handle()` contract is enforced by a test
(`tests/unit/test_detectors.py::TestDetectorContract`): every detector must
declare one. `from __future__ import annotations`, module docstrings, and the
`<verb>_cmd` naming are **not** machine-enforced — they are manual conventions
verified in review.

______________________________________________________________________

## 22. Known deviations and deferred decisions

These are real inconsistencies that were left in place deliberately, because
resolving them would change observable behavior, a public contract, or carry
risk out of proportion to the benefit. They are documented so they are not
"fixed" accidentally without a decision.

1. **No `subprocess` timeout on read-only queries or `Cleaner` removals** (§13).
   Adding one changes behavior; a destructive `conda env remove` must be allowed
   to finish. Revisit only with an explicit, generous per-call timeout.
1. **`Environment.name` is full-path for walk detectors, short for tool
   detectors** (§16). Normalising it would change `list`/JSON output and tests.
1. **JSON `environment count` key differs** across `stats` (`total_count`) and
   `doctor` (`total_environments`) (§19). Changing either breaks its JSON
   contract.
1. **Two "delete everything" flows**: root `killpy --delete-all` (uses
   `rich.prompt.Confirm`) and `killpy delete` (uses `click.confirm`). Different
   prompt libraries, subtly different decline semantics. Unifying is a UX change.
1. **No central `KNOWN_TYPES` registry** (§7). `type` tags are literals kept in
   sync with `_TYPE_ALIASES` by hand; a registry is a larger refactor.
1. **`managed_by` is an open `str`, not an enum/`Literal`** (§16), unlike
   `category`. Both are defensible; leaving it matches the open nature of `type`.
1. **`ERROR`-level logs for "cannot inspect <dir>"** in the iterdir detectors
   (poetry/pyenv/pipenv/hatch/uv) are arguably WARNING per §14; not changed to
   avoid altering log output that may be asserted on downstream.
1. **`Scanner` imports the private `_pyenv_root`** from `detectors.pyenv` to
   flag the active pyenv version. A cross-module private import; acceptable
   until a public accessor is warranted.

When you act on any of these, do it as an explicit, isolated change with its own
justification — not as a drive-by during unrelated work.
