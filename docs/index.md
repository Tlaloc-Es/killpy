# killpy

<div align="center">
	<img src="assets/images/logo.png" alt="killpy logo" width="420">
</div>

`killpy` is a Python environment cleaner for developers who want to find and remove old virtual environments, Conda environments, Poetry environments, pipx packages, pyenv versions, caches, and build artifacts.

If you have ever searched for terms such as `delete old virtualenvs`, `find large conda environments`, `remove Poetry cache envs`, `clean pipx packages`, or `free disk space from Python`, this is the problem space `killpy` targets.

Instead of jumping between `conda`, Poetry cache directories, `pipx`, `pyenv`, and ad hoc shell commands, `killpy` gives you one scanner and one cleanup workflow.

## Why `killpy` exists

Python tooling tends to scatter disk usage across many locations:

- local `.venv` folders inside projects
- directories containing `pyvenv.cfg`
- Poetry-managed environments in cache directories
- Conda environments outside your repo tree
- `pipx` package environments
- `pyenv` versions
- tox, Hatch, Pipenv, and uv environments
- stale caches and Python build artifacts

For many developers, these directories grow for months or years and turn into hidden disk usage. `killpy` is designed to make that usage visible, measurable, and removable.

## What it covers

- Local `.venv` directories and any directory containing `pyvenv.cfg`
- Poetry virtual environments
- Conda environments
- `pipx` package environments
- `pyenv` versions
- Pipenv, Hatch, tox, and uv environments
- Cache directories and Python build artifacts in the CLI scanner flow

This makes `killpy` useful as a Python cleanup tool, Python disk usage inspector, and Python environment inventory CLI.

## Interfaces

`killpy` has two primary surfaces:

- An interactive Textual TUI launched by the top-level `killpy` command
- Scriptable CLI subcommands for listing, deleting, stats, and cache cleanup

The TUI is optimized for inspection and explicit deletion. The scanner and non-interactive commands expose the broader detection model.

## Common search intents this tool answers

- How do I find old Python virtual environments on my machine?
- How do I delete unused Conda environments safely?
- How do I inspect `pipx` package size?
- How do I clean Python caches and build artifacts?
- How do I measure Python environment disk usage from the command line?

## Important behavior notes

- The TUI currently shows environment results plus a dedicated `pipx` tab.
- Cache and artifact detection exists in the scanner and CLI flows, but those do not have separate TUI tables today.
- `killpy clean` removes `__pycache__` directories recursively under the target path.
- Environments managed by external tools are deleted through those tools when possible, such as `conda env remove` and `pipx uninstall`.

## Quickstart

```bash
pipx run killpy --path ~
```

```bash
uvx killpy --path ~
```

Continue with the [Quickstart](getting-started/quickstart.md) for the main workflows, read the [Use Cases](user-guide/use-cases.md) for SEO-friendly real-world examples, or jump to the [CLI reference](user-guide/cli.md).

If `killpy` saves you time or disk space, the GitHub repository is here: [Tlaloc-Es/killpy](https://github.com/Tlaloc-Es/killpy).
