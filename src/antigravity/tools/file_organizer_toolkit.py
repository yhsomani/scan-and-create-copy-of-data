#!/usr/bin/env python3
"""
File Organizer Toolkit
======================
A comprehensive, menu-driven file organization and management application.
Modernized with pathlib and optimized algorithms.

Integrated Features:
- File prefix management (add/remove folder name prefixes)
- Smart file movement (move files into folders based on naming patterns)
- File hierarchy organization (move files up/down directory levels)
- Duplicate suffix removal (efficient regex-based detection)
- Empty folder detection and removal
- Comprehensive error handling and user feedback
"""

import os
import shutil
import re
import sys
import uuid
from pathlib import Path
from typing import List, Dict, Tuple, Optional, Set
import hashlib

# ============================================================================
# CONSTANTS & CONFIG
# ============================================================================

IMAGE_EXTENSIONS: Set[str] = {
    ".png", ".jpg", ".jpeg", ".gif", ".bmp",
    ".webp", ".tiff", ".tif", ".heic"
}

# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def get_valid_path(prompt: str, must_exist: bool = True) -> Optional[Path]:
    """Get and validate a directory path from user input."""
    while True:
        path_str = input(prompt).strip().strip('"').strip("'")
        if not path_str:
            print("❌ Path cannot be empty.")
            continue
        
        path = Path(path_str).resolve()
        
        if path.exists():
            if path.is_dir():
                return path
            else:
                print(f"❌ '{path}' exists but is not a directory.")
        else:
            if must_exist:
                print(f"❌ Path '{path}' does not exist.")
            else:
                create = input(f"Path '{path}' does not exist. Create it? (y/n): ").strip().lower()
                if create == 'y':
                    try:
                        path.mkdir(parents=True, exist_ok=True)
                        print(f"✓ Directory created: {path}")
                        return path
                    except Exception as e:
                        print(f"❌ Failed to create directory: {e}")
                else:
                    return None

def get_valid_int(prompt: str, min_val: int, max_val: int) -> int:
    """Get valid integer input within specified range."""
    while True:
        try:
            choice = int(input(prompt))
            if min_val <= choice <= max_val:
                return choice
            print(f"❌ Invalid choice. Enter a number between {min_val} and {max_val}.")
        except ValueError:
            print("❌ Invalid input. Please enter a valid number.")

def is_excluded(path: Path) -> bool:
    """Check if file should be excluded from suffix removal (images/screenshots)."""
    return (
        path.suffix.lower() in IMAGE_EXTENSIONS or
        path.stem.lower().startswith("screenshot")
    )

# ============================================================================
# FILE ORGANIZATION OPERATIONS
# ============================================================================

def prefix_files_with_folder(root_path: Path) -> int:
    """Add parent folder name as prefix to all files (recursive)."""
    print(f"\n📁 Adding folder name prefix in: {root_path}")
    count = 0
    
    # We use a list to avoid issues with renaming while iterating
    for path in list(root_path.rglob("*")):
        if path.is_file():
            folder_name = path.parent.name
            if not path.name.startswith(f"{folder_name} - "):
                new_name = f"{folder_name} - {path.name}"
                new_path = path.with_name(new_name)
                try:
                    path.rename(new_path)
                    print(f"✓ Renamed: {path.name} → {new_name}")
                    count += 1
                except Exception as e:
                    print(f"❌ Error: {e}")
    return count

def remove_folder_prefixes(root_path: Path) -> int:
    """Remove parent folder name prefix from all files (recursive)."""
    print(f"\n📁 Removing folder name prefix in: {root_path}")
    count = 0
    
    for path in list(root_path.rglob("*")):
        if path.is_file():
            prefix = f"{path.parent.name} - "
            if path.name.startswith(prefix):
                new_name = path.name[len(prefix):]
                new_path = path.with_name(new_name)
                
                # Collision handling
                while new_path.exists():
                    new_name = f"{new_path.stem}_copy{new_path.suffix}"
                    new_path = path.with_name(new_name)
                
                try:
                    path.rename(new_path)
                    print(f"✓ Renamed: {path.name} → {new_name}")
                    count += 1
                except Exception as e:
                    print(f"❌ Error: {e}")
    return count

def organize_into_folders(root_dir: Path, iterative: bool = False) -> int:
    """Move files into folders based on 'FolderName - filename' pattern."""
    print(f"\n📁 Organizing files into named folders: {root_dir}")
    pattern = re.compile(r'^(.+?) - (.+)$')
    total_moved = 0

    while True:
        moved_in_pass = 0
        # Only look at immediate children for this operation to keep it predictable
        for path in list(root_dir.iterdir()):
            if path.is_file():
                match = pattern.match(path.name)
                if match:
                    folder_name, original_name = match.groups()
                    target_dir = root_dir / folder_name
                    target_dir.mkdir(exist_ok=True)
                    
                    target_path = target_dir / original_name
                    while target_path.exists():
                        target_path = target_dir / f"{target_path.stem}_copy{target_path.suffix}"
                    
                    try:
                        shutil.move(str(path), str(target_path))
                        print(f"✓ Moved: {path.name} → {target_dir.name}/")
                        moved_in_pass += 1
                        total_moved += 1
                    except Exception as e:
                        print(f"❌ Error: {e}")

        if not iterative or moved_in_pass == 0:
            break
    return total_moved

def flatten_directory_one_level(root_dir: Path) -> int:
    """Move all files from subdirectories one level up."""
    print(f"\n📁 Moving files up one level: {root_dir}")
    count = 0
    
    # Gather files first to avoid walking into directories we just moved files into
    files_to_move = []
    for path in root_dir.rglob("*"):
        if path.is_file() and path.parent != root_dir:
            # Parent of parent is one level up
            dest_dir = path.parent.parent
            # Security check: don't move outside root
            if not str(dest_dir.resolve()).startswith(str(root_dir.resolve())):
                continue
                
            dest_path = dest_dir / path.name
            while dest_path.exists():
                dest_path = dest_dir / f"{dest_path.stem}_{uuid.uuid4().hex[:4]}{dest_path.suffix}"
            
            files_to_move.append((path, dest_path))

    for src, dest in files_to_move:
        try:
            shutil.move(str(src), str(dest))
            print(f"✓ Moved: {src.relative_to(root_dir)} → {dest.relative_to(root_dir)}")
            count += 1
        except Exception as e:
            print(f"❌ Error: {e}")
            
    return count

def clean_filename_suffixes(root_path: Path) -> int:
    """Efficiently remove (1), (2), etc. suffixes using regex."""
    print(f"\n📁 Removing duplicate suffixes from: {root_path}")
    # Matches (1), (2), etc. at the end of the stem
    suffix_pattern = re.compile(r'\s*\(\d+\)$')
    count = 0
    
    for path in list(root_path.rglob("*")):
        if path.is_file() and not is_excluded(path):
            new_stem = suffix_pattern.sub("", path.stem)
            if new_stem != path.stem:
                new_path = path.with_name(f"{new_stem}{path.suffix}")
                
                # Collision handling
                while new_path.exists():
                    new_stem = f"{new_path.stem}_ref"
                    new_path = path.with_name(f"{new_stem}{path.suffix}")
                
                try:
                    path.rename(new_path)
                    print(f"✓ Cleaned: {path.name} → {new_path.name}")
                    count += 1
                except Exception as e:
                    print(f"❌ Error: {e}")
    return count

def purge_empty_directories(root_path: Path) -> int:
    """Delete all empty folders recursively."""
    print(f"\n📁 Purging empty folders in: {root_path}")
    count = 0
    # Walk bottom-up to catch folders that become empty after their children are deleted
    for path in sorted(root_path.rglob("*"), key=lambda p: len(p.parts), reverse=True):
        if path.is_dir() and path.name not in ['$RECYCLE.BIN', '.git']:
            try:
                if not any(path.iterdir()):
                    path.rmdir()
                    print(f"✓ Deleted empty: {path.relative_to(root_path)}")
                    count += 1
            except OSError:
                pass # Usually permission or non-empty
    return count

def flatten_directory_to_root(root_dir: Path) -> int:
    """Move all files from all subdirectories directly into the root directory."""
    print(f"\n📁 Flattening all files to root: {root_dir}")
    count = 0
    # Gather all files in subdirectories
    files = [p for p in root_dir.rglob("*") if p.is_file() and p.parent != root_dir]
    
    for src in files:
        dest = root_dir / src.name
        # Collision handling
        while dest.exists():
            dest = root_dir / f"{dest.stem}_{uuid.uuid4().hex[:4]}{dest.suffix}"
        try:
            shutil.move(str(src), str(dest))
            print(f"✓ {src.relative_to(root_dir)} → root/")
            count += 1
        except Exception as e:
            print(f"❌ Error moving {src.name}: {e}")
    return count

def run_system_cleanup() -> int:
    """Execute the Windows System Cleanup utility."""
    script_path = Path(__file__).parent / "system_cleanup.bat"
    if not script_path.exists():
        print(f"❌ Cleanup script not found at {script_path}")
        return 0
    
    print(f"\n🚀 Launching System Cleanup: {script_path}")
    try:
        import subprocess
        # Start in a new window to show output and handle admin prompt
        os.startfile(str(script_path))
        return 1
    except Exception as e:
        return 0

def get_file_hash(path: Path) -> str:
    """Calculate SHA-256 hash of a file."""
    h = hashlib.sha256()
    try:
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                h.update(chunk)
        return h.hexdigest()
    except Exception:
        return ""

def deduplicate_files(root_dir: Path) -> int:
    """Find and remove duplicate files based on their SHA-256 hash."""
    print(f"\n📁 Deduplicating files in: {root_dir}")
    hashes: Dict[str, Path] = {}
    count = 0
    
    for path in root_dir.rglob("*"):
        if path.is_file():
            file_hash = get_file_hash(path)
            if not file_hash:
                continue
                
            if file_hash in hashes:
                print(f"🗑️ Removing duplicate: {path.relative_to(root_dir)} (Matches {hashes[file_hash].name})")
                try:
                    path.unlink()
                    count += 1
                except Exception as e:
                    print(f"❌ Error deleting {path.name}: {e}")
            else:
                hashes[file_hash] = path
    return count

def rename_to_hash(root_dir: Path) -> int:
    """Rename all files to their SHA-256 hash, keeping their extension."""
    print(f"\n📁 Renaming files to hash in: {root_dir}")
    count = 0
    
    for path in list(root_dir.rglob("*")):
        if path.is_file():
            file_hash = get_file_hash(path)
            if not file_hash:
                continue
                
            new_name = f"{file_hash}{path.suffix}"
            if path.name == new_name:
                continue
                
            new_path = path.with_name(new_name)
            while new_path.exists() and new_path != path:
                # If a file with this hash name already exists, it's a duplicate. We can just append a copy number, or ignore.
                new_path = path.with_name(f"{file_hash}_copy{uuid.uuid4().hex[:4]}{path.suffix}")
                
            try:
                path.rename(new_path)
                print(f"✓ Renamed: {path.name} → {new_path.name}")
                count += 1
            except Exception as e:
                print(f"❌ Error renaming {path.name}: {e}")
    return count

# ============================================================================
# MENU SYSTEM
# ============================================================================

def display_menu():
    print("\n" + "═" * 60)
    print("  File Organizer Toolkit v2.0")
    print("═" * 60)
    menu = [
        "Add Folder Prefix",
        "Remove Folder Prefix",
        "Move Into Named Folders (Single)",
        "Move Into Named Folders (Iterative)",
        "Move Files Up One Level",
        "Flatten EVERYTHING to Root",
        "Workflow: Move Down (Iterative)",
        "Workflow: Rename & Move Up (Iterative)",
        "Remove Duplicate Suffixes (Regex)",
        "Delete Empty Folders",
        "Deduplicate Files (SHA-256)",
        "Rename Files to Hash",
        "System Cleanup (Admin)",
        "Exit"
    ]
    for i, item in enumerate(menu, 1):
        print(f" {i:2}. {item}")
    print("─" * 60)

def main():
    while True:
        display_menu()
        choice = get_valid_int("Choice (1-14): ", 1, 14)
        
        if choice == 14:
            print("\n👋 Goodbye!")
            break
        
        if choice == 13:
            run_system_cleanup()
            input("\nPress Enter to continue...")
            continue
            
        path = get_valid_path("Enter folder path: ")
        if not path: continue
        
        ops_count = 0
        if choice == 1:
            ops_count = prefix_files_with_folder(path)
        elif choice == 2:
            ops_count = remove_folder_prefixes(path)
        elif choice == 3:
            ops_count = organize_into_folders(path, False)
        elif choice == 4:
            ops_count = organize_into_folders(path, True)
        elif choice == 5:
            ops_count = flatten_directory_one_level(path)
        elif choice == 6:
            ops_count = flatten_directory_to_root(path)
        elif choice == 7:
            m = organize_into_folders(path, True)
            r = remove_folder_prefixes(path)
            ops_count = m + r
        elif choice == 8:
            a = prefix_files_with_folder(path)
            m = flatten_directory_one_level(path)
            ops_count = a + m
        elif choice == 9:
            ops_count = clean_filename_suffixes(path)
        elif choice == 10:
            confirm = input("⚠️ Delete ALL empty folders? (y/n): ").lower()
            if confirm == 'y':
                ops_count = purge_empty_directories(path)
        elif choice == 11:
            confirm = input("⚠️ Delete duplicate files permanently? (y/n): ").lower()
            if confirm == 'y':
                ops_count = deduplicate_files(path)
        elif choice == 12:
            ops_count = rename_to_hash(path)
        
        print(f"\n✨ Done! Operations performed: {ops_count}")
        input("\nPress Enter to continue...")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nAborted by user.")
        sys.exit(0)
