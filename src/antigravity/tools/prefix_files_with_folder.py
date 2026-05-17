#!/usr/bin/env python3
"""
Prefix Files with Folder Name
=============================
Recursively adds the parent folder's name as a prefix to all files.
"""
from pathlib import Path

def prefix_files_with_folder(root: Path) -> int:
    count = 0
    for path in list(root.rglob("*")):
        if path.is_file():
            prefix = f"{path.parent.name} - "
            if not path.name.startswith(prefix):
                new_path = path.with_name(f"{prefix}{path.name}")
                try:
                    path.rename(new_path)
                    print(f"✓ {path.name} -> {new_path.name}")
                    count += 1
                except Exception as e: print(f"❌ {e}")
    return count

if __name__ == "__main__":
    p = input("Path: ").strip().strip('"')
    if p: print(f"Done: {prefix_files_with_folder(Path(p))}")
