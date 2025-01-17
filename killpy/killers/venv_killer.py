import shutil
from datetime import datetime

from killpy.files import format_size, get_total_size
from killpy.killers.killer import BaseKiller


class VenvKiller(BaseKiller):
    def __init__(self, root_dir):
        self.root_dir = root_dir

    def list_environments(self):
        venvs = []
        for dir_path in self.root_dir.rglob(".venv"):
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
