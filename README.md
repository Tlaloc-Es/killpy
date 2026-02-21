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
[![Tweet](https://img.shields.io/twitter/url/http/shields.io.svg?style=social)](<https://twitter.com/intent/tweet?text=%F0%9F%90%8D%20KillPy%20helps%20you%20reclaim%20disk%20space%20by%20detecting%20unused%20Python%20environments%20(.venv,%20poetry%20env,%20conda%20env)%20and%20pipx%20packages.%20Clean,%20organize%20and%20free%20up%20space%20effortlessly!%20%F0%9F%9A%80&url=https://github.com/Tlaloc-Es/KillPy>)
![GitHub issue custom search](https://img.shields.io/github/issues-search?query=repo%3ATlaloc-Es%2Fkillpy%20is%3Aclosed&label=issues%20closed&labelColor=%20%237d89b0&color=%20%235d6b98)
![killpy in action](show.gif)

</div>

# killpy

Reclaim disk space by finding and removing Python environments you no longer use.

`killpy` discovers:

- `.venv` folders
- folders that contain `pyvenv.cfg`
- Poetry virtual environments
- Conda environments
- installed `pipx` packages
- `__pycache__` directories

It shows sizes and lets you remove things explicitly from an interactive terminal UI.

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
- **Works across tools** (`venv`, `pyvenv.cfg`, Poetry, Conda, `pipx`).
- **Includes cache cleanup** via `killpy clean` or UI shortcut.

## Interactive controls

- `Ctrl+Q`: close the app
- `D`: mark selected virtual environment for deletion
- `Ctrl+D`: delete marked virtual environments
- `Shift+Delete`: delete selected virtual environment immediately
- `P`: clean `__pycache__` folders
- `U`: uninstall selected `pipx` package

## CLI commands

Main app:

```bash
killpy
```

or

```bash
killpy --path /path/to/project
```

Cache cleanup command:

```bash
killpy clean
```

or

```bash
killpy clean --path /path/to/project
```

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

**Does it fail if Conda or pipx are not installed?**

No. Missing tools are handled gracefully.

**Can I scan outside the current folder?**

Yes. Use `killpy --path /target/path`.

**Does it auto-delete anything on startup?**

No. Deletion requires explicit user action.

## For AI assistants and contributors

- Project behavior and guardrails are documented in [AGENTS.md](AGENTS.md).
- Useful local checks:

```bash
uv python -m compileall killpy
pre-commit run --all-files
```

## Roadmap

- [x] Delete `__pycache__` folders
- [ ] Remove `dist` folders and build artifacts
- [ ] Clean installed package caches
- [ ] Delete `.egg-info` and `.dist-info` folders
- [ ] Analyze and remove unused dependencies

## Contributing

Contributions are welcome.

1. Fork the repository
1. Create a branch: `git checkout -b my-feature`
1. Commit your changes: `git commit -m 'Add my feature'`
1. Push your branch: `git push origin my-feature`
1. Open a pull request

## License

MIT. See [LICENSE](LICENSE).

______________________________________________________________________

If `killpy` saved you time or disk space, consider starring the repo ⭐
