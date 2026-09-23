from datetime import datetime
from collections import defaultdict

def format_size(size):
    units = ["B", "KB", "MB", "GB", "TB"]
    value = float(size)
    for unit in units:
        if value < 1024 or unit == units[-1]:
            return f"{value:.2f} {unit}"
        value /= 1024
    return f"{value:.2f} TB"

def generate_report(target, folder, files, duplicates):
    total_size = sum(item["size"] for item in files)
    duplicate_count = sum(len(group) - 1 for group in duplicates)
    duplicate_size = sum(item["size"] for group in duplicates for item in group[1:])

    categories = defaultdict(lambda: {"count": 0, "size": 0})
    for item in files:
        categories[item["category"]]["count"] += 1
        categories[item["category"]]["size"] += item["size"]

    lines = [
        "FILESENSE SCAN REPORT",
        "=" * 60,
        f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"Folder: {folder}",
        "",
        "SUMMARY",
        "-" * 60,
        f"Total files: {len(files)}",
        f"Total storage: {format_size(total_size)}",
        f"Duplicate files: {duplicate_count}",
        f"Potential recoverable storage: {format_size(duplicate_size)}",
        "",
        "CATEGORIES",
        "-" * 60,
    ]

    for category, data in sorted(categories.items()):
        lines.append(
            f"{category}: {data['count']} files, {format_size(data['size'])}"
        )

    lines += ["", "DUPLICATES", "-" * 60]

    if not duplicates:
        lines.append("No duplicate groups found.")
    else:
        for index, group in enumerate(duplicates, 1):
            lines.append(f"\nGroup {index}:")
            for item in group:
                lines.append(
                    f"  {item['name']} | {format_size(item['size'])} | {item['path']}"
                )

    lines += ["", "LARGEST FILES", "-" * 60]

    for item in sorted(files, key=lambda x: x["size"], reverse=True)[:20]:
        lines.append(
            f"{item['name']} | {format_size(item['size'])} | {item['path']}"
        )

    with open(target, "w", encoding="utf-8") as file:
        file.write("\n".join(lines))
