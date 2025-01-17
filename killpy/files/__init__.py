from pathlib import Path


def get_total_size(path: Path) -> int:
    total_size = 0
    for f in path.rglob("*"):
        try:
            if f.is_file():
                total_size += f.stat().st_size
        except FileNotFoundError:
            continue
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
