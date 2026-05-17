#!/usr/bin/env python3
"""
Clean Duplicate Suffixes
========================
Efficiently cleans up duplicate file suffixes (e.g., (1), (2), (4))
while excluding images and screenshots.
"""

import sys
import re
from pathlib import Path
from typing import Set

IMAGE_EXTENSIONS: Set[str] = {
    ".png", ".jpg", ".jpeg", ".gif", ".bmp",
    ".webp", ".tiff", ".tif", ".heic"
}

def is_excluded(path: Path) -> bool:
    """Check if file should be excluded (images/screenshots)."""
    return (
        path.suffix.lower() in IMAGE_EXTENSIONS or
        path.stem.lower().startswith("screenshot")
    )

def clean_filename_suffixes(root_path: Path, target_suffix: str = None) -> int:
    """
    Removes duplicate suffixes.
    If target_suffix is provided (e.g. "(4)"), only that suffix is removed.
    Otherwise, any numeric suffix in parentheses is removed.
    """
    print(f"\n📁 Cleaning suffixes in: {root_path}")
    
    if target_suffix:
        # Escape for regex
        escaped = re.escape(target_suffix)
        pattern = re.compile(rf"\s*{escaped}$")
    else:
        # Default: match any (number) at the end
        pattern = re.compile(r"\s*\(\d+\)$")
        
    count = 0
    # Walk bottom-up to ensure we don't change parent names before children
    for path in list(root_path.rglob("*")):
        if path.is_file() and not is_excluded(path):
            new_stem = pattern.sub("", path.stem)
            if new_stem != path.stem:
                new_path = path.with_name(f"{new_stem}{path.suffix}")
                
                # Simple collision handling
                while new_path.exists():
                    new_stem = f"{new_path.stem}_fixed"
                    new_path = path.with_name(f"{new_stem}{path.suffix}")
                
                try:
                    path.rename(new_path)
                    print(f"✓ Renamed: {path.name} → {new_path.name}")
                    count += 1
                except Exception as e:
                    print(f"❌ Error renaming {path.name}: {e}")
                    
    return count

def main():
    path_str = input("Enter the directory path: ").strip().strip('"')
    if not path_str:
        return

    root = Path(path_str).resolve()
    if not root.is_dir():
        print("❌ Invalid directory.")
        return

    suffix = input("Suffix to remove (e.g. '(4)') [Leave blank for any (number)]: ").strip()
    
    count = clean_filename_suffixes(root, suffix if suffix else None)
    print(f"\n✨ Done! Files processed: {count}")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nAborted.")
