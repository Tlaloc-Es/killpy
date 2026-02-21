import json
import logging
import subprocess
from pathlib import Path

from killpy.files import format_size, get_total_size
from killpy.killers.killer import BaseKiller


class PipxKiller(BaseKiller):
    def list_environments(self):
        try:
            result = subprocess.run(
                ["pipx", "list", "--json"],
                capture_output=True,
                text=True,
                check=True,
            )

            installed_packages = json.loads(result.stdout)

            packages_with_size = []
            for package_name, package_data in installed_packages.get(
                "venvs", {}
            ).items():
                app_paths = (
                    package_data.get("metadata", {})
                    .get("main_package", {})
                    .get("app_paths", [])
                )
                if not app_paths:
                    continue

                bin_path = app_paths[0].get("__Path__", "")
                if not bin_path:
                    continue

                package_path = Path(bin_path).parent
                if package_path.exists():
                    total_size = get_total_size(package_path)
                    formatted_size = format_size(total_size)
                    packages_with_size.append(
                        (package_name, total_size, formatted_size)
                    )

            return packages_with_size

        except subprocess.CalledProcessError as e:
            logging.error("Error:  %s", e)
            return []
        except Exception as e:
            logging.error("An error occurred: %s", e)
            return []

    def remove_environment(self, env_to_delete):
        try:
            subprocess.run(
                ["pipx", "uninstall", env_to_delete],
                check=True,
            )
        except subprocess.CalledProcessError as e:
            logging.error("Error: %s", e)
