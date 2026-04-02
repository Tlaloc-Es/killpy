# Automation

`killpy` can be used as an interactive cleanup tool, but it also has enough CLI surface for automation.

## Inventory jobs

Generate machine-readable output:

```bash
killpy list --path ~/projects --json
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
