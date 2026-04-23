# Automation

`killpy` can be used as an interactive cleanup tool, but it also has enough CLI surface for automation.

## Pre-commit hooks

`killpy` ships four hooks for [pre-commit](https://pre-commit.com/).

```yaml
- repo: https://github.com/Tlaloc-Es/KillPy
  rev: 0.20.0
  hooks:
    - id: killpy                  # remove __pycache__ on every commit
    - id: killpy-clean-caches     # all cache dirs: .mypy_cache, .pytest_cache, .ruff_cache …
    - id: killpy-clean-artifacts  # dist/, build/, *.egg-info
    - id: killpy-remove-venv      # local .venv — manual stage only
```

| Hook id | What it removes | Stage |
|---------|-----------------|-------|
| `killpy` | `__pycache__` directories | `pre-commit` |
| `killpy-clean-caches` | All local cache dirs | `pre-commit` |
| `killpy-clean-artifacts` | Build artifacts | `pre-commit` |
| `killpy-remove-venv` | Local `.venv` environments | `manual` |

`killpy-remove-venv` is set to the `manual` stage to avoid destroying your environment on every commit. Trigger it explicitly when you want to reset:

```bash
pre-commit run killpy-remove-venv --hook-stage manual
```

## Inventory jobs

Generate machine-readable output:

```bash
killpy list --path ~/projects --json
```

Progress messages go to **stderr**, so stdout is clean for piping. Add `--quiet` / `-q` to suppress progress entirely:

```bash
killpy list --path ~/projects --json --quiet | jq '.[] | .size_human'
```

Stream results progressively:

```bash
killpy list --path ~/projects --json-stream | jq
```

## Reporting jobs

Aggregate environment size by type:

```bash
killpy stats --path ~/projects --json
```

## Scheduled cleanup previews

Preview deletions before applying them:

```bash
killpy delete --path ~/projects --older-than 180 --dry-run
```

## Bulk cleanup

For explicit scripted cleanup:

```bash
killpy --path ~/projects --delete-all --yes
```

Use that mode only when the scan root and retention policy are already controlled elsewhere.
