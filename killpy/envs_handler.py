import subprocess
from datetime import datetime
from pathlib import Path


def remove_duplicates(venvs):
    seen_paths = set()
    unique_venvs = []

    for venv in venvs:
        venv_path = venv[0]
        if venv_path not in seen_paths:
            unique_venvs.append(venv)
            seen_paths.add(venv_path)

    return unique_venvs


def get_total_size(path: Path) -> int:
    total_size = sum(f.stat().st_size for f in path.rglob("*") if f.is_file())
    return total_size


def format_size(size_in_bytes: int):
    if size_in_bytes >= 1 << 30:
        return f"{size_in_bytes / (1 << 30):.2f} GB"
    elif size_in_bytes >= 1 << 20:
        return f"{size_in_bytes / (1 << 20):.2f} MB"
    elif size_in_bytes >= 1 << 10:
        return f"{size_in_bytes / (1 << 10):.2f} KB"
    else:
        return f"{size_in_bytes} bytes"


def find_venvs(base_directory: Path):
    venvs = []
    for dir_path in base_directory.rglob(".venv"):
        last_modified_timestamp = dir_path.stat().st_mtime
        last_modified = datetime.fromtimestamp(last_modified_timestamp).strftime(
            "%d/%m/%Y"
        )
        size = get_total_size(dir_path)
        size_to_show = format_size(size)
        venvs.append((dir_path, ".venv", last_modified, size, size_to_show))
        venvs.sort(key=lambda x: x[2], reverse=True)

    return venvs


def find_venvs_with_pyvenv(base_directory: Path):
    venvs = []
    for dir_path in base_directory.rglob("pyvenv.cfg"):
        venv_dir = dir_path.parent
        last_modified_timestamp = dir_path.stat().st_mtime
        last_modified = datetime.fromtimestamp(last_modified_timestamp).strftime(
            "%d/%m/%Y"
        )
        size = get_total_size(venv_dir)
        size_to_show = format_size(size)
        venvs.append((venv_dir, "pyvenv.cfg", last_modified, size, size_to_show))

    venvs.sort(key=lambda x: x[2], reverse=True)
    return venvs


def remove_conda_env(env_name):
    try:
        subprocess.run(
            ["conda", "env", "remove", "-n", env_name],
            check=True,
        )
    except subprocess.CalledProcessError as e:
        print(f"Error: {e}")


def list_conda_environments():
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
