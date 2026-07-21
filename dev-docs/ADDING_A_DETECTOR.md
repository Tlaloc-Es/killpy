# Adding a new detector

> **Audience:** Developers and coding agents adding support for a new kind of
> Python environment/cache to killpy.
> **See also:** `CODING_CONVENTIONS.md` §5 (detector contract), §6 (`can_handle`),
> §7 (`type` strings), §8 (sorting), §12 (exceptions), §16 (models).

A *detector* discovers one kind of Python environment or cache directory and
turns each hit into an `Environment`. The `Scanner` owns everything else
(dedup, exclusions, system-critical flagging, sorting, progress), so a detector
only has to answer two questions: *"can I run here?"* (`can_handle`) and
*"what did I find?"* (`detect`).

______________________________________________________________________

## 1. Checklist

1. Create `killpy/detectors/<name>.py`. First line is a module docstring,
   second is `from __future__ import annotations` (§1).
1. Subclass `AbstractDetector` and set a unique `name` class attribute.
1. **Declare** the `can_handle()` contract as data — do **not** write a
   `can_handle()` method (§6). Pick one of the four shapes in §3 below.
1. Implement `detect(self, path: Path) -> list[Environment]` (§4 below).
1. Register the class in `killpy/detectors/__init__.py`: import it, add it to
   `__all__`, and append it to `ALL_DETECTORS`.
1. If the `Environment.type` you emit is different from `name`, add the mapping
   to `_TYPE_ALIASES` in `killpy/commands/_utils.py` (§6 below), or `--type <name>` will match nothing.
1. Add tests. `tests/unit/test_detectors.py::TestDetectorContract` already
   enforces that you declared a contract; add behaviour tests for `detect()`.
1. Run `poe lint && poe type && poe test`.

______________________________________________________________________

## 2. Declaring the `can_handle()` contract

`can_handle()` lives once in `AbstractDetector` and is computed from what you
declare. Return value means *"is it even possible for me to find anything on
this machine?"* — it is a cheap gate, never a health check, and must never
raise. Choose the shape that matches your tool:

```python
# always True — pure filesystem walk (venv, tox, cache, artifacts)
class FooDetector(AbstractDetector):
    name = "foo"
    always_available = True

# tool — needs a CLI on PATH (conda, pipx)
class FooDetector(AbstractDetector):
    name = "foo"
    required_tool = "foo"

# directory — scans one global directory (poetry, pyenv)
class FooDetector(AbstractDetector):
    name = "foo"
    def _candidate_dirs(self) -> tuple[Path, ...]:
        return (_foo_home(),)

# tool-or-directory — CLI installed OR its data dir exists (pipenv, hatch, uv)
class FooDetector(AbstractDetector):
    name = "foo"
    required_tool = "foo"
    def _candidate_dirs(self) -> tuple[Path, ...]:
        return (_foo_home(),)
```

Why `_candidate_dirs()` is a method and not a `dirs = (_foo_home,)` attribute:
it is called at *runtime*, so the path helper is resolved late and tests that
`patch("killpy.detectors.foo._foo_home")` are honoured. A tuple of function
references captured at class-definition time would silently ignore the patch.

______________________________________________________________________

## 3. Implementing `detect()`

Rules (all from the conventions doc):

- Signature `def detect(self, path: Path) -> list[Environment]`. Return a
  **`list`, never a generator** (§5).
- **Never raise.** Catch the specific expected errors and log at DEBUG
  (`(FileNotFoundError, OSError)`, plus `subprocess.CalledProcessError` /
  `json.JSONDecodeError` when relevant), returning what you have so far (§12).
- **Do not sort** — the Scanner sorts once (§8).
- Walk with `os.walk(..., topdown=True)` and prune with the shared
  `VCS_PRUNE_DIRS` / `ENV_INTERNAL_DIRS` from `base.py`; never `rglob` (§3, §4).
- Get sizes with `get_total_size()` (§3); never format sizes yourself (§17).
- If the tool manages its own deletion, set `managed_by="<tool>"` so `Cleaner`
  routes through the tool instead of `shutil.rmtree` (§10).
- If `detect()` ignores `path` (global-cache detectors), mark it
  `# noqa: ARG002`.
- `name` field: filesystem-walk detectors store the full path string; global
  detectors store a short identifier (§16).

______________________________________________________________________

## 4. Worked example (hybrid contract, global directory)

Illustrative: a tool `foo` whose environments live under `~/.foo/envs` and which
manages its own removal (`foo env remove <name>`). Adapt the paths to the real
tool.

```python
"""Detector for foo-managed environments."""

from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from pathlib import Path

from killpy.detectors.base import AbstractDetector
from killpy.files import get_total_size
from killpy.models import Environment

logger = logging.getLogger(__name__)


def _foo_envs_dir() -> Path:
    """Return foo's environments directory, honouring ``FOO_HOME``."""
    override = os.environ.get("FOO_HOME")
    base = Path(override).expanduser() if override else Path.home() / ".foo"
    return base / "envs"


class FooDetector(AbstractDetector):
    """Detects foo-managed environments (global ``~/.foo/envs`` directory).

    The scan *path* argument is ignored.
    """

    name = "foo"
    required_tool = "foo"  # tool-or-directory contract

    def _candidate_dirs(self) -> tuple[Path, ...]:
        # ...or its global environments directory exists.
        return (_foo_envs_dir(),)

    def detect(self, path: Path) -> list[Environment]:  # noqa: ARG002
        root = _foo_envs_dir()
        if not root.exists():
            return []

        envs: list[Environment] = []
        try:
            for env_dir in root.iterdir():
                if not env_dir.is_dir():
                    continue
                try:
                    stat = env_dir.stat()
                    envs.append(
                        Environment(
                            path=env_dir,
                            name=env_dir.name,
                            type="foo",
                            last_modified=datetime.fromtimestamp(
                                stat.st_mtime, tz=timezone.utc
                            ),
                            size_bytes=get_total_size(env_dir),
                            managed_by="foo",  # Cleaner must run `foo env remove`
                        )
                    )
                except (FileNotFoundError, OSError) as exc:
                    logger.debug("Skipping foo env %s: %s", env_dir, exc)
        except OSError as exc:
            logger.debug("Cannot inspect foo envs dir %s: %s", root, exc)
            return []
        return envs
```

Then register it (`killpy/detectors/__init__.py`):

```python
from killpy.detectors.foo import FooDetector
# ...add "FooDetector" to __all__ and to ALL_DETECTORS...
```

If `managed_by="foo"`, also add the removal strategy to `Cleaner`
(`cleaner.py`) and route it in `Cleaner.delete()` (§10), plus its `_remove_foo`
subprocess helper following §13.

Because this detector emits `type == name == "foo"`, no `_TYPE_ALIASES` entry is
needed. Add one only when the emitted tag differs from `name` (like
`VenvDetector` → `".venv"`/`"pyvenv.cfg"`, or `CacheDetector`'s subtypes).

______________________________________________________________________

## 5. Special cases, the escape hatch, and when to rethink the model

The declarative contract covers *"a CLI is on PATH and/or a directory exists"* —
which is every current detector. Two situations go beyond it:

### The escape hatch: override `can_handle()`

If applicability genuinely can't be expressed with the three knobs — e.g. it
depends on an environment variable, on the *combination* of two conditions with
`and`, or on a file's contents — then **override `can_handle()` for that one
detector** as a documented exception:

```python
class WeirdDetector(AbstractDetector):
    name = "weird"

    def can_handle(self) -> bool:
        # Escape hatch: needs BOTH the CLI and an opt-in env var — the
        # declarative knobs only express OR, so we override here on purpose.
        return shutil.which("weird") is not None and "WEIRD_ENABLE" in os.environ
```

Rules for an override:

- Keep the gate cheap and side-effect-free: only `which()` / `exists()` /
  reading an env var. It must **never raise** (wrap anything risky and return
  `False`).
- Add a comment starting with `# Escape hatch:` explaining *why* it can't be
  declarative — otherwise the next reader will "fix" it back.
- You do **not** also set the knobs. The contract test
  (`test_every_detector_declares_a_contract`) already accepts an overridden
  `can_handle()` as a valid, deliberate declaration.

This is the "two styles coexisting" case: the declarative form is the default;
an override is a rare, labelled exception. One or two overrides across the
package is fine.

### When to rethink the whole model

Treat these as signals that the base abstraction — not the individual detector —
needs to change:

- **Three or more** detectors need `can_handle()` overrides. At that point the
  declarative model is fighting reality; consider replacing the three knobs with
  a single predicate, e.g. `applies_when: Callable[[], bool] | None`, or moving
  back to a per-detector method with the *enforcement test* still guaranteeing
  each detector states its intent.
- The knobs start multiplying (`required_tools` plural, `required_files`,
  `required_env_vars`, …). A short, growing list of ad-hoc knobs is a smell;
  a single predicate or a small `AppliesWhen` value object is cleaner.
- A detector needs to *combine* conditions with `and`/`not` rather than the
  base's fixed `or`. The base intentionally only expresses OR; anything else is
  the escape hatch's job, and repeated need means the base model is too rigid.

If you reach one of these, don't bolt another special case onto `base.py` in
passing — raise it as an explicit design change (its own PR/decision), update
this guide and `CODING_CONVENTIONS.md` §6, and adjust the enforcement test to
match the new model.
