import shutil
from pathlib import Path

from killpy.files import get_total_size


def remove_pycache(path: Path) -> int:
    total_freed_space = 0
    for pycache_dir in path.rglob("__pycache__"):
        try:
            total_freed_space += get_total_size(pycache_dir)
            shutil.rmtree(pycache_dir)
        except Exception:
            continue
    return total_freed_space
