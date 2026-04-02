# Installation

## Requirements

- Python 3.10 or newer
- Optional external tools if you want those integrations detected or removed:
  - `conda`
  - `pipx`

If those tools are not installed, their detectors are skipped cleanly.

## Install with pip

```bash
pip install killpy
```

## Install with pipx

```bash
pipx install killpy
```

## Install with uv

```bash
uv tool install killpy
```

## Verify the install

```bash
killpy --help
```

## Local development install

From the repository root:

```bash
uv sync --all-groups
```

```bash
uv run killpy --help
```
