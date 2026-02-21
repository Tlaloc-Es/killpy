from datetime import datetime

from killpy.files import format_size, get_total_size
from killpy.killers.venv_killer import VenvKiller


class PyenvKiller(VenvKiller):
    def __init__(self, root_dir):
        super().__init__(root_dir)

    def list_environments(self):
        venvs = []
        for dir_path in self._iter_files_named("pyvenv.cfg"):
            venv_dir = dir_path.parent
            last_modified_timestamp = dir_path.stat().st_mtime
            last_modified = datetime.fromtimestamp(last_modified_timestamp).strftime(
                "%d/%m/%Y"
            )
            size = get_total_size(venv_dir)
            size_to_show = format_size(size)
            venvs.append((venv_dir, "pyvenv.cfg", last_modified, size, size_to_show))

        venvs.sort(key=lambda x: x[3], reverse=True)
        return venvs
