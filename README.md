<div align="center">

</div>

```plaintext
█  ▄ ▄ █ █ ▄▄▄▄  ▄   ▄              ____
█▄▀  ▄ █ █ █   █ █   █           .'`_ o `;__,
█ ▀▄ █ █ █ █▄▄▄▀  ▀▀▀█ .       .'.'` '---'  '
█  █ █ █ █ █     ▄   █  .`-...-'.'Reclaim disk space by cleaning unused Python environments.
           ▀      ▀▀▀    `-...-'
```

<div align="center">

[![PyPI](https://img.shields.io/pypi/v/killpy.svg)](https://pypi.org/project/killpy/)
[![Downloads](https://static.pepy.tech/personalized-badge/killpy?period=month&units=international_system&left_color=grey&right_color=blue&left_text=PyPi%20Downloads)](https://pepy.tech/project/killpy)
[![Stars](https://img.shields.io/github/stars/Tlaloc-Es/killpy?color=yellow&style=flat)](https://github.com/Tlaloc-Es/killpy/stargazers)
[![Coverage](https://codecov.io/gh/Tlaloc-Es/killpy/branch/master/graph/badge.svg)](https://codecov.io/gh/Tlaloc-Es/killpy)
[![Tweet](https://img.shields.io/twitter/url/http/shields.io.svg?style=social)](<https://twitter.com/intent/tweet?text=%F0%9F%90%8D%20KillPy%20helps%20you%20reclaim%20disk%20space%20by%20detecting%20unused%20Python%20environments%20(.venv,%20poetry%20env,%20conda%20env)%20and%20pipx%20packages.%20Clean,%20organize%20and%20free%20up%20space%20effortlessly!%20%F0%9F%9A%80&url=https://github.com/Tlaloc-Es/KillPy>)
![GitHub issue custom search](https://img.shields.io/github/issues-search?query=repo%3ATlaloc-Es%2Fkillpy%20is%3Aclosed&label=issues%20closed&labelColor=%20%237d89b0&color=%20%235d6b98)
![killpy in action](show.gif)

</div>

## Star History

[![Star History Chart](https://api.star-history.com/svg?repos=Tlaloc-Es/killpy&type=date&legend=bottom-right)](https://www.star-history.com/#Tlaloc-Es/killpy&type=date&legend=bottom-right)

# killpy

Reclaim disk space by finding and removing Python environments you no longer use.

`killpy` discovers:

| Type | What is detected |
|------|-----------------|
| `venv` | `.venv` directories and any folder containing `pyvenv.cfg` |
| `poetry` | Poetry virtual environments (`~/.cache/pypoetry/virtualenvs`) |
| `conda` | Conda environments reported by `conda env list` |
| `pipx` | Installed `pipx` packages |
| `pyenv` | pyenv-managed Python versions (`~/.pyenv/versions`) |
| `pipenv` | Pipenv virtualenvs (`~/.local/share/virtualenvs`) |
| `hatch` | Hatch environments (`~/.local/share/hatch/env`) |
| `uv` | uv virtual environments (`.venv` created by `uv`) |
| `tox` | tox environments (`.tox` directories) |
| `cache` | `__pycache__`, `.mypy_cache`, `.pytest_cache`, `.ruff_cache`, global pip/uv caches |
| `artifacts` | `dist`, `build`, `.egg-info`, `.dist-info` folders |

It shows sizes and lets you remove items explicitly — either interactively via the TUI or non-interactively from the command line.

## Quickstart

Install:

```bash
pip install killpy
```

Run from current directory:

```bash
killpy
```

Scan a specific path:

```bash
killpy --path /path/to/project
```

Without installing:

```bash
pipx run killpy
```

or

```bash
uvx killpy
```

## Why use killpy

- **Fast discovery** of Python environments with size metadata.
- **Safer cleanup flow** with explicit mark/delete actions.
- **Works across tools** (`venv`, Poetry, Conda, `pipx`, `pyenv`, Pipenv, Hatch, uv, tox).
- **CLI and TUI** — scan, filter and delete from the terminal UI or pipe-friendly commands.
- **Includes cache cleanup** — removes `__pycache__`, tool caches and build artifacts.

## Interactive TUI

Launch the interactive terminal UI:

```bash
killpy
# or
killpy --path /path/to/project
```

### Keyboard shortcuts

| Key | Action |
|-----|--------|
| `Ctrl+Q` | Close the app |
| `D` | Mark selected environment for deletion |
| `Ctrl+D` | Delete all marked environments |
| `Shift+Delete` | Delete selected environment immediately |
| `P` | Clean `__pycache__` folders |
| `U` | Uninstall selected `pipx` package |

## CLI commands

### `killpy list` — list environments

```bash
killpy list
killpy list --path /path/to/project
killpy list --type venv --type conda   # filter by type (repeatable)
killpy list --older-than 90            # only environments not accessed in 90+ days
killpy list --json                     # machine-readable JSON output
```

### `killpy delete` — non-interactive deletion

```bash
killpy delete                          # confirm prompt before deleting
killpy delete --yes                    # skip confirmation
killpy delete --dry-run                # preview — nothing is deleted
killpy delete --type venv              # limit to a specific type
killpy delete --older-than 180 --yes   # delete stale envs without prompt
killpy delete --path /path/to/project
```

### `killpy stats` — disk-usage summary

```bash
killpy stats
killpy stats --path /path/to/project
killpy stats --json
```

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

### `killpy clean` — remove cache directories

```bash
killpy clean
killpy clean --path /path/to/project
```

Removes `__pycache__` directories recursively under the target path.

## Safety

`killpy` performs destructive actions (environment/package/cache deletion).
Always review selected items before confirming removal.
You are responsible for files deleted on your system.

## Pre-commit hook

Use `killpy clean` before each commit to remove cache directories:

```yml
- repo: https://github.com/Tlaloc-Es/KillPy
  rev: 0.15.7
  hooks:
    - id: killpy
      pass_filenames: false
```

## FAQ

**Does it fail if Conda, pipx or pyenv are not installed?**

No. Missing tools and directories are handled gracefully — the detector is simply skipped.

**Can I scan outside the current folder?**

Yes. Use `--path /target/path` on any command.

**Does it auto-delete anything on startup?**

No. Deletion always requires an explicit user action (TUI key press, `--yes` flag or interactive confirmation).

**Can I use it in scripts / CI?**

Yes. Use `killpy list --json` or `killpy delete --yes` for non-interactive use.

**Can I combine filters?**

Yes. For example:

```bash
killpy delete --type venv --older-than 90 --dry-run
```

## For AI assistants and contributors

- Project behavior and guardrails are documented in [AGENTS.md](AGENTS.md).
- Useful local checks:

```bash
uv run python -m compileall killpy
uv run pytest
pre-commit run --all-files
```

## Roadmap

### Done

- [x] Interactive TUI with mark/delete workflow
- [x] Delete `__pycache__` folders (`killpy clean`)
- [x] Detect and remove `dist`, `build`, `.egg-info` and `.dist-info` artifacts
- [x] Detect global pip and uv caches
- [x] CLI command `killpy list` with `--json`, `--type`, `--older-than`
- [x] CLI command `killpy delete` with `--dry-run`, `--yes`, `--type`, `--older-than`
- [x] CLI command `killpy stats` — grouped disk-usage report
- [x] Detectors for Hatch, uv, Pipenv, tox, pyenv
- [x] Unit test suite (Scanner / Cleaner / Detectors / Commands)

### Planned

- [ ] `killpy list --sort size|date|name` — configurable sort order
- [ ] `killpy delete --interactive` — checkbox-style selector inside the CLI
- [ ] Detect unused dependencies inside `pyproject.toml` / `requirements.txt`
- [ ] Windows support improvements (pyenv-win, conda on Windows PATH)
- [ ] `--min-size` filter (`killpy list --min-size 500MB`)
- [ ] Shell completions (bash, zsh, fish)
- [ ] GitHub Actions CI matrix (Linux × macOS × Windows, Python 3.12–3.13)
- [ ] TUI: filter panel (by type, search by name/path)
- [ ] TUI: live progress bar while scanning
- [ ] TUI: confirmation dialog showing total bytes to be freed
- [ ] TUI: summary panel (total envs, total size, breakdown by type)
- [ ] Config file (`~/.config/killpy/config.toml`) for default scan path and ignored dirs
- [ ] `killpy export` — save scan results to JSON/CSV for auditing

## Contributing

Contributions are welcome.

1. Fork the repository
1. Create a branch: `git checkout -b my-feature`
1. Commit your changes: `git commit -m 'Add my feature'`
1. Run the tests: `uv run pytest`
1. Push your branch: `git push origin my-feature`
1. Open a pull request

## License

MIT. See [LICENSE](LICENSE).

______________________________________________________________________

If `killpy` saved you time or disk space, consider starring the repo ⭐
