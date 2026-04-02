# Quickstart

## Run without installing

```bash
pipx run killpy --path ~
```

```bash
uvx killpy --path ~
```

The `--path` option controls the filesystem root scanned by the TUI or command.

## Launch the TUI

```bash
killpy
```

```bash
killpy --path ~/projects
```

The TUI starts immediately and streams results as detectors finish. You do not need to wait for the full scan to complete before browsing rows.

## Common CLI workflows

List everything under a path:

```bash
killpy list --path ~/projects
```

Preview a cleanup without deleting anything:

```bash
killpy delete --path ~/projects --dry-run
```

Show size totals grouped by type:

```bash
killpy stats --path ~/projects
```

Remove `__pycache__` directories recursively:

```bash
killpy clean --path ~/projects
```

## Headless cleanup

The top-level command also provides a bulk delete mode:

```bash
killpy --path ~/projects --delete-all
```

```bash
killpy --path ~/projects --delete-all --yes
```

Use this mode carefully. It scans first, prints the candidates, and optionally asks for confirmation before deleting them all.
