<div align="center">

![Logo](https://raw.githubusercontent.com/Tlaloc-Es/killpy/master/logo.png)

### Free GBs of disk space by removing unused Python environments

Find and delete old `.venv`, conda, poetry, pipenv, uv and more — safely, in seconds.

```bash
uvx killpy --path ~
```

**killpy is [npkill](https://github.com/voidcosmos/npkill) for Python** — but it understands every environment manager, instead of matching folders by name.

> ⭐ Featured in [awesome-python](https://github.com/vinta/awesome-python) — a curated list of the best Python tools

[Documentation](https://tlaloc-es.github.io/killpy/)

[![PyPI](https://img.shields.io/pypi/v/killpy.svg)](https://pypi.org/project/killpy/)
[![Python](https://img.shields.io/pypi/pyversions/killpy.svg)](https://pypi.org/project/killpy/)
[![Downloads](https://static.pepy.tech/personalized-badge/killpy?period=total&units=international_system&left_color=grey&right_color=blue&left_text=Downloads)](https://pepy.tech/project/killpy)
[![Stars](https://img.shields.io/github/stars/Tlaloc-Es/killpy?color=yellow&style=flat)](https://github.com/Tlaloc-Es/killpy/stargazers)
[![Coverage](https://codecov.io/gh/Tlaloc-Es/killpy/branch/master/graph/badge.svg)](https://codecov.io/gh/Tlaloc-Es/killpy)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Tweet](https://img.shields.io/twitter/url/http/shields.io.svg?style=social)](https://twitter.com/intent/tweet?text=%F0%9F%90%8D%20killpy%20is%20npkill%20for%20Python%20%E2%80%94%20find%20and%20delete%20unused%20venv,%20conda,%20poetry,%20pipx%20and%20pyenv%20environments%20and%20free%2010%E2%80%9340%20GB%20of%20disk%20space.%20Try%20it:%20uvx%20killpy%20--path%20~&url=https://github.com/Tlaloc-Es/killpy)
[![Awesome Python](https://awesome.re/badge.svg)](https://github.com/vinta/awesome-python)

![killpy in action](https://raw.githubusercontent.com/Tlaloc-Es/killpy/master/docs/gifs/demo.gif)

</div>

______________________________________________________________________

## Table of Contents

- [The Problem](#the-problem)
  - [What killpy detects](#what-killpy-detects)
- [Quickstart](#quickstart)
- [killpy vs alternatives](#killpy-vs-alternatives)
- [Interactive TUI](#interactive-tui)
  - [Keyboard shortcuts](#keyboard-shortcuts)
  - [Search / filter](#search--filter)
  - [Multi-select mode](#multi-select-mode)
- [CLI cheatsheet](#cli-cheatsheet)
- [FAQ](#faq)
- [Roadmap](#roadmap)
- [Pre-commit hooks](#pre-commit-hooks)
- [Safety](#safety)
- [Contributing](#contributing)

______________________________________________________________________

## The Problem

If you have been writing Python for more than a year, your disk is probably full of environments you forgot about.

Every project gets a `.venv`. Every tutorial leaves a Conda environment behind. Every `poetry install` creates a hidden virtualenv somewhere in `~/.cache`. `pyenv` versions stack up. `tox` creates a `.tox` folder in every repo you ever tested. `__pycache__` directories scatter everywhere. Build artifacts from old `pip install -e .` runs stay forever.

**None of these get cleaned up automatically.**

A typical developer machine accumulates **10–40 GB** of Python environments over a few years — most of them abandoned and completely useless.

`killpy` scans your filesystem, shows you everything with its size, and lets you delete it — either from a slick interactive terminal UI or via a single headless command.

That makes it useful if you are trying to:

- find old Python virtual environments
- delete unused Conda environments
- inspect Poetry environment disk usage
- clean up `pipx` package environments
- remove Python caches and build artifacts
- free disk space consumed by Python development tools

```bash
pipx run killpy --path ~
# or
uvx killpy --path ~
```

### What killpy detects

`killpy` supports **11 environment types** across every major Python tool:

| Type | What is detected | Typical location |
|------|-----------------|-----------------|
| `venv` | `.venv` dirs and any folder containing `pyvenv.cfg` | project root |
| `poetry` | Poetry virtual environments | `~/.cache/pypoetry/virtualenvs` |
| `conda` | Conda environments (`conda env list`) | `~/anaconda3/envs`, `~/miniconda3/envs` |
| `pipx` | Installed `pipx` packages | `~/.local/share/pipx/venvs` |
| `pyenv` | pyenv-managed Python versions | `~/.pyenv/versions` |
| `pipenv` | Pipenv virtualenvs | `~/.local/share/virtualenvs` |
| `hatch` | Hatch environments | `~/.local/share/hatch/env` |
| `uv` | uv tool environments (`uv tool install`) and uv-managed Pythons | `~/.local/share/uv` |
| `tox` | tox environments | `.tox/` inside repo |
| `cache` | `__pycache__`, `.mypy_cache`, `.pytest_cache`, `.ruff_cache`, plus global pip/uv caches when the scanned path contains them | project tree, `~/.cache` |
| `artifacts` | `dist/`, `build/`, `.egg-info`, `.dist-info` | project root |

______________________________________________________________________

## Quickstart

**Instant run — no install needed:**

```bash
pipx run killpy
# or
uvx killpy
```

**Install permanently:**

```bash
pip install killpy
# or
pipx install killpy
# or
uv tool install killpy
```

**Scan current directory:**

```bash
killpy
```

**Scan your entire home folder:**

```bash
killpy --path ~
```

**Exclude paths matching a pattern:**

```bash
killpy --path ~ --exclude "backups,archive,work"
```

**Delete everything non-interactively (CI / scripts):**

```bash
killpy --path ~/projects --delete-all --yes
```

Also available as a **pre-commit hook** — see [Pre-commit hooks](#pre-commit-hooks) below.

More documentation: [https://tlaloc-es.github.io/killpy/](https://tlaloc-es.github.io/killpy/)

______________________________________________________________________

## killpy vs alternatives

| Tool | venv | conda | poetry | pipx | pyenv | caches | artifacts | TUI | search | multi-select |
|------|:----:|:-----:|:------:|:----:|:-----:|:------:|:---------:|:---:|:------:|:------------:|
| **killpy** | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| `npkill` | by name | ❌ | ❌ | ❌ | ❌ | `node_modules` by default | by name | ✅ | ✅ | ✅ |
| `pyclean` | ❌ | ❌ | ❌ | ❌ | ❌ | `__pycache__` only | ❌ | ❌ | ❌ | ❌ |
| `conda clean` | ❌ | partial | ❌ | ❌ | ❌ | conda only | ❌ | ❌ | ❌ | ❌ |
| `pip cache purge` | ❌ | ❌ | ❌ | ❌ | ❌ | pip only | ❌ | ❌ | ❌ | ❌ |
| `find . -name .venv -exec rm` | venv only | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |

[npkill](https://github.com/voidcosmos/npkill) is a great tool and pioneered this exact concept for `node_modules`; its `--target` flag can match any folder by name. What it lacks is tool awareness: conda, poetry, pipx and pyenv keep their environments in central locations that folder-name matching cannot discover. killpy knows where each toolchain lives — no other single tool discovers, sizes, and removes environments across **all** major Python toolchains.

______________________________________________________________________

## Interactive TUI

```bash
killpy
killpy --path /path/to/scan
killpy --path ~ --exclude "company-projects"
```

The TUI starts immediately and streams results as each detector finishes — no waiting for a full scan before you can start browsing. Select items, mark them, and confirm; **nothing is deleted without explicit action**.

Environments flagged with `⚠️` are actively in use (the environment killpy runs from, or the pyenv global version) — the TUI shows them but refuses to delete them.

### Keyboard shortcuts

| Key | Action |
|-----|--------|
| `↑` / `↓` or `k` / `j` | Move cursor up / down (vim-style) |
| `/` | Open live search/filter bar (substring match) |
| `Escape` | Close search bar and clear filter |
| `T` | Toggle multi-select mode on / off |
| `Space` | *(Multi-select)* Toggle current row selected |
| `A` | *(Multi-select)* Select all visible / deselect all |
| `D` | Mark highlighted item for deletion |
| `Ctrl+D` | Delete all marked items (or all selected in multi-select mode) |
| `Shift+Delete` | Delete highlighted item immediately, no mark step |
| `o` | Open the item's parent folder in the OS file manager |
| `P` | Remove all `__pycache__` folders under the scanned path |
| `U` | Uninstall the selected `pipx` package |
| `Ctrl+Q` | Quit |

### Search / filter

Press `/` to open the filter bar at the bottom of the screen. Type any text — the venv table filters by path substring (case-insensitive) and updates live as you type. Press `Escape` or submit an empty value to clear the filter and return to the full list.

### Multi-select mode

Press `T` to enter multi-select mode. A status bar shows the current selection count.

- `Space` — toggle the highlighted row
- `A` — select all visible non-deleted rows (press again to deselect all)
- `Ctrl+D` — delete every selected row in one operation
- `T` again — exit multi-select mode (selection is cleared)

Multi-select coexists with the existing `D` / `Ctrl+D` mark-and-delete flow — both work independently.

______________________________________________________________________

## CLI cheatsheet

Everything the TUI does is also scriptable. Start here:

```bash
killpy --path ~                           # interactive TUI over your home folder
```

The one-liners you will actually use:

```bash
killpy list --json                        # every environment, machine-readable
killpy list --min-size 500MB              # only environments worth reclaiming
killpy delete --older-than 180 --yes      # remove stale envs, no prompt
killpy doctor                             # health report — what is safe to delete
killpy stats                              # disk usage breakdown by type
```

**📖 Full CLI reference** — every subcommand (`list`, `find`, `delete`, `stats`, `clean`, `doctor`) with every flag, example outputs, and demos: **[tlaloc-es.github.io/killpy → CLI](https://tlaloc-es.github.io/killpy/user-guide/cli/)**

______________________________________________________________________

## FAQ

**My Mac/Linux disk is almost full — can killpy help?**

Yes. Run `killpy --path ~` to scan your home folder. The `stats` command gives an immediate breakdown of how many GB each env type is consuming. Most developers reclaim 5–30 GB.

**How do I delete all unused virtual environments at once?**

```bash
killpy delete --type venv --older-than 90 --yes
```

Deletes every `.venv` / `pyvenv.cfg` env not modified in the last 90 days, without prompting.

**How do I use killpy in a CI pipeline or script?**

```bash
# List as machine-readable JSON (progress goes to stderr, JSON to stdout)
killpy list --json

# Suppress progress output entirely with --quiet / -q
killpy list --json --quiet | jq '.[] | .size_human'

# Stream results as NDJSON in real time
killpy list --json-stream | jq '.size_bytes'

# Delete everything without a TUI
killpy --path ./build_artifacts --delete-all --yes
```

Progress messages always go to **stderr**, so stdout is clean for piping even without `--quiet`. Use `-q` when you want no output at all on stderr.

**How do I skip certain directories?**

```bash
killpy --path ~ --exclude "company,production,do-not-touch"
```

Any environment whose path contains one of the comma-separated patterns is silently skipped.

**How do I clean up Poetry virtualenvs?**

Poetry stores virtualenvs in `~/.cache/pypoetry/virtualenvs`. killpy detects and deletes them automatically — no manual path hunting required.

```bash
killpy list --type poetry
killpy delete --type poetry --older-than 60
```

**How do I find all `.venv` folders on my computer?**

```bash
killpy list --type venv --path ~
```

Or for a quick JSON export:

```bash
killpy list --type venv --path ~ --json
```

**How do I free up disk space used by Conda?**

```bash
killpy list --type conda        # inspect
killpy delete --type conda      # delete selected
```

`killpy` runs `conda env list` internally and lets you delete individual environments. Alternatively, `killpy --path ~` will surface them in the TUI.

**Can I combine filters?**

Yes. For example:

```bash
killpy delete --type venv --older-than 90 --dry-run
```

**How do I remove all `__pycache__` folders recursively?**

```bash
killpy clean --path /path/to/project
```

Or press `P` in the TUI to clean them for the scanned path.

**What does ⚠️ mean next to an environment?**

The environment is currently in use — it is the environment killpy itself runs from, or your pyenv global version. killpy shows it so you are aware of it, but refuses to delete it: the TUI always skips it, and `killpy delete` / `--delete-all` skip it unless you pass `--force`.

**Does it fail if Conda, pipx or pyenv are not installed?**

No. Missing tools are handled gracefully — that detector is simply skipped. You get results for everything that is available on the system.

**Does killpy auto-delete anything?**

Never. Deletion always requires an explicit action: a key press in the TUI, `--yes` on the CLI, or an interactive prompt. killpy is fully read-only on startup.

**Can I preview what would be deleted without actually deleting?**

```bash
killpy delete --dry-run
```

Nothing is removed. You see exactly what would happen.

**How do I disable the one-line hint shown after deletions?**

Set `KILLPY_NO_HINT=1`. The hint is a single line shown only in interactive terminals — it never appears in pipes, scripts, JSON output, or CI.

**Why is Python using so much disk space?**

Each virtual environment is a full copy (or symlinked tree) of a Python interpreter plus all installed packages. A typical project `.venv` with common dependencies weighs 200 MB–1 GB. Multiply by dozens of projects and you get tens of gigabytes — all orphaned when the project is archived.

______________________________________________________________________

## Roadmap

Development happens in the open — the [issue tracker](https://github.com/Tlaloc-Es/killpy/issues) **is** the roadmap: new filters and flags for the CLI, TUI improvements, better Windows support, and more.

Want to contribute? Start with a [good first issue](https://github.com/Tlaloc-Es/killpy/issues?q=is%3Aissue+is%3Aopen+label%3A%22good+first+issue%22) — each one is small, scoped, and comes with pointers to the relevant code.

Missing a detector for your favourite tool? Propose it in the [detector ideas thread](https://github.com/Tlaloc-Es/killpy/discussions/43).

______________________________________________________________________

## Pre-commit hooks

`killpy` ships four hooks for [pre-commit](https://pre-commit.com/). Add the ones you need to your `.pre-commit-config.yaml`:

```yaml
- repo: https://github.com/Tlaloc-Es/killpy
  rev: 1.2.0
  hooks:
    - id: killpy                  # remove __pycache__ on every commit
    - id: killpy-clean-caches     # also removes .mypy_cache, .pytest_cache, .ruff_cache
    - id: killpy-clean-artifacts  # remove dist/, build/, *.egg-info before committing
    - id: killpy-remove-venv      # remove .venv (manual stage — see below)
```

| Hook id | What it removes | Default stage |
|---------|-----------------|---------------|
| `killpy` | `__pycache__` directories | `pre-commit` |
| `killpy-clean-caches` | All local cache dirs (`__pycache__`, `.mypy_cache`, `.pytest_cache`, `.ruff_cache`) | `pre-commit` |
| `killpy-clean-artifacts` | Build artifacts (`dist/`, `build/`, `*.egg-info`) | `pre-commit` |
| `killpy-remove-venv` | Local `.venv` environments | `manual` |

**`killpy-remove-venv`** is staged as `manual` because deleting the environment on every commit would require you to recreate it each time. Run it explicitly when you want a clean slate:

```bash
pre-commit run killpy-remove-venv --hook-stage manual
```

Typical minimal setup (safe for daily use):

```yaml
- repo: https://github.com/Tlaloc-Es/killpy
  rev: 1.2.0
  hooks:
    - id: killpy
```

Add `killpy-clean-artifacts` if your project generates `dist/` or `build/` locally and you want to guarantee they are never staged by accident.

______________________________________________________________________

## Safety

`killpy` performs **destructive, irreversible** actions. Always review the selection before confirming removal. The `--dry-run` flag lets you preview everything safely. Environments marked `⚠️` are actively in use and are skipped by every delete path unless you explicitly pass `--force`.

**You are responsible for files deleted on your system.**

______________________________________________________________________

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for the full guide — setup, workflow, how to add a new detector, and GIF recording instructions.

```bash
# Quick local checks
uv run python -m compileall killpy
uv run pytest
pre-commit run --all-files
```

Project architecture and guardrails are documented in [AGENTS.md](AGENTS.md).

______________________________________________________________________

## License

MIT. See [LICENSE](LICENSE).

______________________________________________________________________

<div align="center">

## ⭐ If killpy saved you disk space, a star helps others find it

[![GitHub stars](https://img.shields.io/github/stars/Tlaloc-Es/killpy?style=social)](https://github.com/Tlaloc-Es/killpy/stargazers)

Stars help `killpy` appear when developers search for Python disk cleanup tools.
It takes 2 seconds and makes a real difference for discoverability.

[⭐ Star on GitHub](https://github.com/Tlaloc-Es/killpy)

</div>

______________________________________________________________________

## Star History

[![Star History Chart](https://api.star-history.com/svg?repos=Tlaloc-Es/killpy&type=Date)](https://star-history.com/#Tlaloc-Es/killpy&Date)
