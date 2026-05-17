#!/usr/bin/env python3
"""
Delete Empty Folders
====================
Recursively finds and deletes all empty folders.
"""

import sys
from pathlib import Path

def purge_empty_directories(root_path: Path) -> int:
    print(f"\n📁 Searching for empty folders in: {root_path}")
    count = 0
    
    # Bottom-up traversal ensures we catch parent folders that become empty
    # after their empty children are removed.
    for path in sorted(root_path.rglob("*"), key=lambda p: len(p.parts), reverse=True):
        if path.is_dir() and path.name not in ['$RECYCLE.BIN', '.git']:
            try:
                # Check if directory is empty
                if not any(path.iterdir()):
                    path.rmdir()
                    print(f"✓ Deleted: {path.relative_to(root_path)}")
                    count += 1
            except OSError as e:
                # Permission errors or non-empty (if created during walk)
                pass
                
    return count

def main():
    path_str = input("Enter the directory path to purge: ").strip().strip('"')
    if not path_str:
        return

    root = Path(path_str).resolve()
    if not root.is_dir():
        print("❌ Invalid directory.")
        return

    confirm = input(f"⚠️  This will delete ALL empty folders in {root}. Continue? (y/n): ").lower()
    if confirm == 'y':
        count = purge_empty_directories(root)
        print(f"\n✨ Done! Empty folders removed: {count}")
    else:
        print("Cancelled.")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nAborted.")
