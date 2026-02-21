import os
import shutil
from datetime import datetime
from pathlib import Path

from killpy.files import format_size, get_total_size
from killpy.killers.killer import BaseKiller


class VenvKiller(BaseKiller):
    EXCLUDED_DIRS = {
        ".git",
        ".hg",
        ".svn",
        "node_modules",
        ".tox",
        ".nox",
        ".mypy_cache",
        ".pytest_cache",
        "__pycache__",
        ".ruff_cache",
        "dist",
        "build",
    }

    def __init__(self, root_dir):
        self.root_dir = Path(root_dir)

    def _iter_dirs_named(self, target_name: str):
        for current_root, directories, _ in os.walk(self.root_dir, topdown=True):
            directories[:] = [
                directory
                for directory in directories
                if directory not in self.EXCLUDED_DIRS
            ]
            if target_name in directories:
                yield Path(current_root) / target_name

    def _iter_files_named(self, file_name: str):
        for current_root, directories, files in os.walk(self.root_dir, topdown=True):
            directories[:] = [
                directory
                for directory in directories
                if directory not in self.EXCLUDED_DIRS
            ]
            if file_name in files:
                yield Path(current_root) / file_name

    def list_environments(self):
        venvs = []
        for dir_path in self._iter_dirs_named(".venv"):
            try:
                dir_path.resolve(strict=True)
                last_modified_timestamp = dir_path.stat().st_mtime
                last_modified = datetime.fromtimestamp(
                    last_modified_timestamp
                ).strftime("%d/%m/%Y")
                size = get_total_size(dir_path)
                size_to_show = format_size(size)
                venvs.append((dir_path, ".venv", last_modified, size, size_to_show))
            except FileNotFoundError:
                continue
        venvs.sort(key=lambda x: x[3], reverse=True)
        return venvs

    def remove_environment(self, env_to_delete):
        try:
            shutil.rmtree(env_to_delete)
        except FileNotFoundError:
            pass
