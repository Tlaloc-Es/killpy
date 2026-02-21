import logging
import platform
from datetime import datetime
from pathlib import Path

from killpy.files import format_size, get_total_size
from killpy.killers.venv_killer import VenvKiller

logger = logging.getLogger(__name__)


class PoetryKiller(VenvKiller):
    def __init__(self, root_dir):
        super().__init__(root_dir)

    def list_environments(self):
        if platform.system() == "Windows":
            poetry_venvs_dir = (
                Path.home() / "AppData" / "Local" / "pypoetry" / "virtualenvs"
            )
        else:
            poetry_venvs_dir = Path.home() / ".cache" / "pypoetry" / "virtualenvs"

        if not poetry_venvs_dir.exists():
            logger.debug(
                "No Poetry virtual environments directory found at %s",
                poetry_venvs_dir,
            )
            return []

        venvs = []
        try:
            for venv_path in poetry_venvs_dir.iterdir():
                if not venv_path.is_dir():
                    continue
                try:
                    last_modified_timestamp = venv_path.stat().st_mtime
                    last_modified = datetime.fromtimestamp(
                        last_modified_timestamp
                    ).strftime("%d/%m/%Y")
                    size = get_total_size(venv_path)
                    size_to_show = format_size(size)
                    venvs.append(
                        (venv_path, "poetry", last_modified, size, size_to_show)
                    )
                except (FileNotFoundError, OSError) as error:
                    logger.debug(
                        "Skipping inaccessible poetry environment '%s': %s",
                        venv_path,
                        error,
                    )
                    continue

            venvs.sort(key=lambda x: x[3], reverse=True)
            return venvs

        except OSError as error:
            logger.error("Unable to inspect poetry virtual environments: %s", error)
            return []
