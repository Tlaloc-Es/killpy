# Use Cases

This page is intentionally written around common search intents so both users and LLM-based tools can quickly match `killpy` to the right workflow.

## Find old Python virtual environments

If you want to find old `.venv` folders or directories containing `pyvenv.cfg`, run:

```bash
killpy list --path ~/projects --type venv
```

This is the simplest workflow when you want to inspect unused virtual environments before deleting anything.

## Delete unused Conda environments

If you want a reviewable cleanup of Conda environments:

```bash
killpy delete --type conda --dry-run
```

When deletion happens, `killpy` uses `conda env remove --name ... --yes` rather than removing those directories blindly.

## Measure Python environment disk usage

If you want to see how much disk space Python environments consume by category:

```bash
killpy stats --path ~/projects
```

This is useful for questions like `how much space do my virtualenvs use` or `what is taking space in my Python setup`.

## Clean Poetry, pipx, and pyenv leftovers

`killpy` also helps when your disk usage is spread across tool-specific locations that are easy to forget:

- Poetry virtual environments
- `pipx` package environments
- `pyenv` versions
- Pipenv, Hatch, tox, and uv environments

Run:

```bash
killpy list --path ~
```

The scanner can combine local project scanning with tool-managed environment discovery.

## Remove Python caches and build artifacts

If you want to clean `__pycache__` directories quickly:

```bash
killpy clean --path ~/projects
```

If you want broader visibility into caches and artifacts before deletion:

```bash
killpy list --path ~/projects --type cache --type artifacts
```

This is the better workflow for users searching for `remove Python cache folders`, `clean build directories`, or `find Python artifacts taking disk space`.

## Build machine-readable inventories

If you need JSON output for scripts, reporting, or other AI agents:

```bash
killpy list --path ~/projects --json
```

Or stream results progressively:

```bash
killpy list --path ~/projects --json-stream
```
