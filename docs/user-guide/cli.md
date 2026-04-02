# CLI

## Top-level command

The top-level command lives in `killpy/__main__.py` and does one of two things:

- launches the TUI by default
- runs a non-interactive bulk delete flow when `--delete-all` is provided

Examples:

```bash
killpy
```

```bash
killpy --path ~ --exclude "archive,backups"
```

```bash
killpy --path ~/projects --delete-all --yes
```

## `killpy list`

Use `list` when you want read-only inspection.

```bash
killpy list --path ~/projects
killpy list --type venv --type conda
killpy list --older-than 90
killpy list --json
killpy list --json-stream
```

`--json-stream` emits NDJSON progressively while the scan runs.

## `killpy delete`

Use `delete` when you want a scriptable delete flow with filtering.

```bash
killpy delete --path ~/projects --dry-run
killpy delete --path ~/projects --type cache --older-than 30
killpy delete --path ~/projects --yes
```

## `killpy stats`

Use `stats` to aggregate counts and sizes by detected type.

```bash
killpy stats --path ~/projects
killpy stats --json
```

## `killpy clean`

Use `clean` to recursively remove `__pycache__` directories.

```bash
killpy clean --path ~/projects
```

This command is narrower than the full cache detector model. It does not currently remove every cache type that the scanner can detect.
