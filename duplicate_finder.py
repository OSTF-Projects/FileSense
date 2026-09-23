from collections import defaultdict
import hashlib
from pathlib import Path

def sha256_file(path, chunk_size=1024 * 1024, max_bytes=None):
    """
    Computes the SHA-256 hash of a file or its prefix.
    If max_bytes is provided, reads only up to max_bytes (useful for quick pass).
    """
    digest = hashlib.sha256()
    bytes_read = 0

    with open(path, "rb") as file:
        while True:
            to_read = chunk_size
            if max_bytes is not None:
                remaining = max_bytes - bytes_read
                if remaining <= 0:
                    break
                to_read = min(chunk_size, remaining)

            chunk = file.read(to_read)
            if not chunk:
                break
            digest.update(chunk)
            bytes_read += len(chunk)

    return digest.hexdigest()

def find_duplicates(files, progress_callback=None):
    """
    Finds duplicate files using a high-performance two-pass hashing strategy:
    1. Group files by exact byte size.
    2. For candidates of the same size, compare a fast 4KB prefix hash.
    3. For candidates with matching prefix hashes, compare the full SHA-256.
    4. Groups are sorted chronologically by modification time (oldest/original first).
    """
    # Group by file size (files must have identical size to be duplicates)
    by_size = defaultdict(list)
    for item in files:
        if item["size"] > 0:  # Skip 0-byte files or handle them if desired
            by_size[item["size"]].append(item)

    # Filter to size groups that have at least 2 files
    candidate_groups = [group for group in by_size.values() if len(group) >= 2]
    total_candidates = sum(len(g) for g in candidate_groups)
    processed = 0

    duplicates = []

    for same_size in candidate_groups:
        # Pass 1: Quick 4KB prefix hash
        quick_hash_groups = defaultdict(list)
        for item in same_size:
            processed += 1
            if progress_callback:
                progress_callback(processed, total_candidates, item.get("name", ""))

            try:
                # 4KB quick hash
                q_hash = sha256_file(item["path"], chunk_size=4096, max_bytes=4096)
                quick_hash_groups[q_hash].append(item)
            except (PermissionError, OSError):
                continue

        # Pass 2: Full SHA-256 hash for items with matching quick hashes
        for q_group in quick_hash_groups.values():
            if len(q_group) < 2:
                continue

            full_hash_groups = defaultdict(list)
            for item in q_group:
                try:
                    f_hash = sha256_file(item["path"])
                    full_hash_groups[f_hash].append(item)
                except (PermissionError, OSError):
                    continue

            for group in full_hash_groups.values():
                if len(group) > 1:
                    # Sort group by modification time: oldest first (original), newer copies follow
                    sorted_group = sorted(group, key=lambda x: x.get("mtime", 0))
                    duplicates.append(sorted_group)

    return duplicates

