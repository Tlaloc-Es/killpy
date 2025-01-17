import subprocess
from datetime import datetime
from pathlib import Path

from killpy.files import format_size, get_total_size
from killpy.killers.killer import BaseKiller


class CondaKiller(BaseKiller):
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
                if line.strip() and not line.startswith("#"):
                    env_info = line.strip().split()
                    env_name = env_info[0]

                    if "*" in env_info:
                        continue

                    dir_path = Path(env_info[1])
                    last_modified_timestamp = dir_path.stat().st_mtime
                    last_modified = datetime.fromtimestamp(
                        last_modified_timestamp
                    ).strftime("%d/%m/%Y")

                    size = get_total_size(dir_path)
                    size_to_show = format_size(size)
                    venvs.append((env_name, "Conda", last_modified, size, size_to_show))

            venvs.sort(key=lambda x: x[3], reverse=True)
            return venvs

        except subprocess.CalledProcessError:
            return []
        except Exception:
            return []

    def remove_environment(self, env_to_delete):
        try:
            subprocess.run(
                ["conda", "env", "remove", "-n", env_to_delete],
                check=True,
            )
        except subprocess.CalledProcessError as e:
            print(f"Error: {e}")
