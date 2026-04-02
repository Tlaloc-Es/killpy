# JSON Output

The `list` command can emit either a JSON array or NDJSON.

## `--json`

```bash
killpy list --json
```

This returns a JSON array of environment objects.

Example shape:

```json
[
  {
    "path": "/home/user/projects/demo/.venv",
    "name": "/home/user/projects/demo/.venv",
    "type": "venv",
    "last_accessed": "2026-04-02T10:00:00",
    "size_bytes": 183500800,
    "size_human": "175.0 MB",
    "managed_by": null,
    "is_system_critical": false
  }
]
```

## `--json-stream`

```bash
killpy list --json-stream
```

This emits one JSON object per line as results become available.

Example:

```json
{"path": "/home/user/projects/demo/.venv", "name": "/home/user/projects/demo/.venv", "type": "venv", "last_accessed": "2026-04-02T10:00:00", "size_bytes": 183500800, "size_human": "175.0 MB", "managed_by": null, "is_system_critical": false}
```

NDJSON is useful when you want to pipe results into `jq` or process them incrementally.
