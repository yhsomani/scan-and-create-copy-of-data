#!/usr/bin/env python3
"""
Flatten Nested Files
====================
Recursively moves all files from subdirectories into the specified root directory.
"""
import shutil
from pathlib import Path
import uuid

def flatten_directory(root: Path) -> int:
    count = 0
    files = [p for p in root.rglob("*") if p.is_file() and p.parent != root]
    for src in files:
        dest = root / src.name
        while dest.exists():
            dest = root / f"{dest.stem}_{uuid.uuid4().hex[:4]}{dest.suffix}"
        try:
            shutil.move(str(src), str(dest))
            print(f"✓ {src.name} -> root/")
            count += 1
        except Exception as e: print(f"❌ {e}")
    return count

if __name__ == "__main__":
    p = input("Path: ").strip().strip('"')
    if p: print(f"Moved: {flatten_directory(Path(p))}")
