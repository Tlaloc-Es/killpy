"""File-size helpers: recursive byte totals and human-readable formatting."""

from __future__ import annotations

import os
from pathlib import Path


def get_total_size(path: Path) -> int:
    """Return the recursive size of *path* in bytes.

    Symlinks are never followed: a link inside an environment must not
    pull in the size of targets outside it (nor create walk loops).  The
    link's own size is what gets counted.
    """
    total_size = 0
    for current_root, _dirs, files in os.walk(path):
        for name in files:
            try:
                total_size += os.lstat(os.path.join(current_root, name)).st_size
            except OSError:
                continue
    return total_size


def format_size(size_bytes: int) -> str:
    """Return *size_bytes* as a human-readable string (GB / MB / KB / bytes)."""
    if size_bytes >= 1 << 30:
        return f"{size_bytes / (1 << 30):.2f} GB"
    elif size_bytes >= 1 << 20:
        return f"{size_bytes / (1 << 20):.2f} MB"
    elif size_bytes >= 1 << 10:
        return f"{size_bytes / (1 << 10):.2f} KB"
    else:
        return f"{size_bytes} bytes"
