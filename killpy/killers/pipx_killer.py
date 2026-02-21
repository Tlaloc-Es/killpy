import json
import logging
import subprocess
from pathlib import Path

from killpy.files import format_size, get_total_size
from killpy.killers.killer import BaseKiller

logger = logging.getLogger(__name__)


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

                try:
                    package_path = Path(bin_path).parent
                    if package_path.exists():
                        total_size = get_total_size(package_path)
                        formatted_size = format_size(total_size)
                        packages_with_size.append(
                            (package_name, total_size, formatted_size)
                        )
                except OSError as error:
                    logger.debug(
                        "Skipping pipx package '%s' due to path error: %s",
                        package_name,
                        error,
                    )
                    continue

            return packages_with_size

        except FileNotFoundError:
            return []
        except json.JSONDecodeError as error:
            logger.error("Invalid JSON output from pipx: %s", error)
            return []
        except subprocess.CalledProcessError as error:
            logger.debug("Failed to list pipx packages: %s", error)
            return []
        except OSError as error:
            logger.debug("Unable to inspect pipx packages: %s", error)
            return []

    def remove_environment(self, env_to_delete):
        try:
            subprocess.run(
                ["pipx", "uninstall", env_to_delete],
                check=True,
            )
        except FileNotFoundError as error:
            logger.error(
                "pipx executable not found while removing '%s': %s",
                env_to_delete,
                error,
            )
        except subprocess.CalledProcessError as error:
            logger.error(
                "Failed to uninstall pipx package '%s': %s",
                env_to_delete,
                error,
            )
        except OSError as error:
            logger.error(
                "OS error while uninstalling pipx package '%s': %s",
                env_to_delete,
                error,
            )
