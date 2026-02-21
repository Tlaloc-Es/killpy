import logging
import subprocess
from datetime import datetime
from pathlib import Path

from killpy.files import format_size, get_total_size
from killpy.killers.killer import BaseKiller

logger = logging.getLogger(__name__)


class CondaKiller(BaseKiller):
    MIN_ENV_INFO_FIELDS = 2

    def list_environments(self):
        try:
            result = subprocess.run(
                ["conda", "env", "list"],
                capture_output=True,
                text=True,
                check=True,
            )

            venvs = []
            for line in result.stdout.splitlines():
                if not line.strip() or line.startswith("#"):
                    continue

                env_info = line.strip().split()
                if "*" in env_info:
                    continue
                if len(env_info) < self.MIN_ENV_INFO_FIELDS:
                    logger.debug("Skipping malformed conda env row: %s", line)
                    continue

                try:
                    env_name = env_info[0]
                    dir_path = Path(env_info[-1])
                    last_modified_timestamp = dir_path.stat().st_mtime
                    last_modified = datetime.fromtimestamp(
                        last_modified_timestamp
                    ).strftime("%d/%m/%Y")

                    size = get_total_size(dir_path)
                    size_to_show = format_size(size)
                    venvs.append((env_name, "Conda", last_modified, size, size_to_show))
                except (FileNotFoundError, OSError) as error:
                    logger.debug(
                        "Skipping inaccessible conda env path '%s': %s",
                        env_info[-1],
                        error,
                    )
                    continue

            venvs.sort(key=lambda x: x[3], reverse=True)
            return venvs

        except FileNotFoundError:
            return []
        except subprocess.CalledProcessError as error:
            logger.debug("Failed to list conda environments: %s", error)
            return []
        except OSError as error:
            logger.debug("Unable to inspect conda environments: %s", error)
            return []

    def remove_environment(self, env_to_delete):
        try:
            subprocess.run(
                ["conda", "env", "remove", "-n", env_to_delete],
                check=True,
            )
        except FileNotFoundError as error:
            logger.error(
                "Conda executable not found while removing '%s': %s",
                env_to_delete,
                error,
            )
        except subprocess.CalledProcessError as error:
            logger.error(
                "Failed to remove conda environment '%s': %s",
                env_to_delete,
                error,
            )
        except OSError as error:
            logger.error(
                "OS error while removing conda environment '%s': %s",
                env_to_delete,
                error,
            )
