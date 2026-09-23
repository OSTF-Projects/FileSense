from pathlib import Path
from datetime import datetime
from organizer import get_category

def scan_folder(folder):
    """
    Recursively scans the target folder and collects file metadata.
    Robustly handles permission errors, broken symlinks, and hidden files.
    """
    results = []
    folder_path = Path(folder).resolve()

    if not folder_path.exists() or not folder_path.is_dir():
        return results

    for path in folder_path.rglob("*"):
        try:
            # Skip directories and broken symlinks
            if path.is_symlink() or not path.is_file():
                continue

            # Calculate relative path safely
            try:
                rel_parts = path.relative_to(folder_path).parts
            except ValueError:
                continue

            # Avoid hidden files and folders (.git, .cache, .DS_Store, etc.)
            if any(part.startswith(".") for part in rel_parts):
                continue

            stat = path.stat()
            results.append({
                "name": path.name,
                "path": path,
                "path_str": str(path),
                "size": stat.st_size,
                "extension": path.suffix.lower(),
                "category": get_category(path.suffix.lower()),
                "mtime": stat.st_mtime,
                "modified": datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S")
            })
        except (PermissionError, OSError):
            continue

    return results

