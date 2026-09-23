from pathlib import Path
import shutil

CATEGORY_MAP = {
    "Documents": {
        ".pdf", ".doc", ".docx", ".txt", ".rtf", ".odt",
        ".xls", ".xlsx", ".csv", ".ppt", ".pptx", ".md", ".epub"
    },
    "Images": {
        ".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp",
        ".svg", ".tiff", ".ico", ".heic", ".psd", ".ai"
    },
    "Videos": {
        ".mp4", ".mkv", ".avi", ".mov", ".wmv", ".flv",
        ".webm", ".m4v", ".ts", ".3gp"
    },
    "Music": {
        ".mp3", ".wav", ".flac", ".aac", ".ogg", ".m4a",
        ".wma", ".opus", ".alac", ".aiff"
    },
    "Archives": {
        ".zip", ".rar", ".7z", ".tar", ".gz", ".bz2",
        ".xz", ".iso", ".dmg"
    },
    "Applications": {
        ".exe", ".msi", ".dmg", ".pkg", ".deb", ".rpm",
        ".app", ".apk"
    },
    "Code": {
        ".py", ".java", ".js", ".ts", ".html", ".css",
        ".php", ".c", ".cpp", ".h", ".hpp", ".cs", ".go",
        ".rs", ".swift", ".kt", ".json", ".xml", ".sql",
        ".yaml", ".yml", ".sh", ".bash", ".zsh"
    },
}

# Distinct modern color tokens for storage visualization & badges
CATEGORY_COLORS = {
    "Documents": "#3b82f6",   # Blue
    "Images": "#ec4899",      # Pink
    "Videos": "#8b5cf6",      # Purple
    "Music": "#f97316",       # Orange
    "Archives": "#eab308",    # Yellow
    "Applications": "#06b6d4",# Cyan
    "Code": "#10b981",        # Emerald
    "Others": "#64748b",      # Slate
}

def get_category(extension):
    extension = extension.lower()
    for category, extensions in CATEGORY_MAP.items():
        if extension in extensions:
            return category
    return "Others"

def unique_destination(destination, source=None):
    # If the destination is the same file as source, no need to rename
    if source and destination.resolve() == source.resolve():
        return destination

    if not destination.exists():
        return destination

    counter = 1
    while True:
        candidate = destination.with_name(
            f"{destination.stem}_{counter}{destination.suffix}"
        )
        if not candidate.exists() or (source and candidate.resolve() == source.resolve()):
            return candidate
        counter += 1

def organize_files(folder, files):
    """
    Moves files into category subdirectories within the specified folder.
    Skips files that are already inside their destination category folder.
    """
    moved = 0
    folder_path = Path(folder).resolve()

    for item in files:
        source = Path(item["path"]).resolve()

        if not source.exists():
            continue

        category = item["category"]
        target_dir = folder_path / category

        # If file is already inside target category folder, do not touch it
        if source.parent.resolve() == target_dir.resolve():
            continue

        target_dir.mkdir(exist_ok=True)
        destination = unique_destination(target_dir / source.name, source=source)

        if source.resolve() == destination.resolve():
            continue

        try:
            shutil.move(str(source), str(destination))
            moved += 1
        except (PermissionError, OSError, shutil.Error):
            continue

    return moved

