import os
import shutil
from pathlib import Path

from killpy.files import get_total_size


def remove_pycache(path: Path) -> int:
    """Remove every ``__pycache__`` directory under *path*.

    The walk never follows symlinks, so a link placed inside the tree
    cannot steer the deletion outside the scanned root.  Failed removals
    are skipped and not counted as freed space.
    """
    total_freed_space = 0
    for current_root, directories, _files in os.walk(path, topdown=True):
        if "__pycache__" not in directories:
            continue
        # Prune it from the walk: it is deleted below, not descended into.
        directories.remove("__pycache__")
        pycache_dir = Path(current_root) / "__pycache__"
        if pycache_dir.is_symlink():
            continue
        try:
            size = get_total_size(pycache_dir)
            shutil.rmtree(pycache_dir)
        except OSError:
            continue
        total_freed_space += size
    return total_freed_space
