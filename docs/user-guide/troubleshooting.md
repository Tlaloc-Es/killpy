# Troubleshooting

## `conda` environments do not appear

The Conda detector only runs when `conda` is available on `PATH`.

Check:

```bash
conda env list
```

If that command does not work in your shell, `killpy` will skip Conda detection.

## `pipx` packages do not appear

The `pipx` detector depends on:

```bash
pipx list --json
```

If `pipx` is unavailable or returns invalid output, the detector is skipped.

## Deletion fails for tool-managed environments

`killpy` deletes some environments through their owning tool:

- Conda via `conda env remove --name ... --yes`
- `pipx` via `pipx uninstall ...`

If those commands fail on their own, `killpy` will surface the error.

## The TUI does not show caches or build artifacts

That is current behavior, not a broken install. Cache and artifact detection exists in the scanner and non-interactive CLI flows, but the TUI only renders environment results and a dedicated `pipx` tab today.

## `killpy clean` removed less than expected

`killpy clean` only removes `__pycache__` directories recursively under the target path. For broader cleanup, use `killpy list`, `killpy delete`, or `killpy stats` to inspect other detected cache and artifact types.
