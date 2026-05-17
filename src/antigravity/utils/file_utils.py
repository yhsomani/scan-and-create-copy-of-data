from __future__ import annotations

import fnmatch
import os
from pathlib import Path
from typing import Callable, Iterable, List, Optional, Set, Tuple


class PathEscapeError(ValueError):
    pass

def validate_pathsafety(path: Path, root: Path) -> bool:
    try:
        resolved = path.resolve()
        root_resolved = root.resolve()
        return resolved.is_relative_to(root_resolved)
    except (ValueError, OSError):
        return False


def validate_input_path(path: Path, root: Path) -> Path:
    if not validate_pathsafety(path, root):
        raise ValueError(f"Path escapes root directory: {path}")
    return path


def normalize_path(path: Path) -> Path:
    return path.expanduser().resolve()


def is_hidden_path(path: Path) -> bool:
    if path.name.startswith("."):
        return True
    if os.name == "nt":
        try:
            import ctypes

            attrs = ctypes.windll.kernel32.GetFileAttributesW(str(path))
            return bool(attrs & 2)
        except Exception:
            return False
    return False


def load_ignore_patterns(root: Path, ignore_file_name: str) -> List[str]:
    ignore_file = root / ignore_file_name
    patterns: List[str] = []
    if not ignore_file.exists():
        return patterns

    try:
        with ignore_file.open("r", encoding="utf-8", errors="ignore") as handle:
            for raw in handle:
                line = raw.strip()
                if not line or line.startswith("#"):
                    continue
                patterns.append(line)
    except PermissionError:
        return patterns
    return patterns


def matches_ignore_patterns(path: Path, root: Path, patterns: Iterable[str]) -> bool:
    if not patterns:
        return False

    relative_path = path.relative_to(root).as_posix()
    filename = path.name
    for pattern in patterns:
        normalized = pattern.strip()
        if not normalized:
            continue
        if fnmatch.fnmatch(relative_path, normalized) or fnmatch.fnmatch(
            filename, normalized
        ):
            return True
        if fnmatch.fnmatch(relative_path, f"**/{normalized}"):
            return True
    return False


def safe_is_binary(path: Path) -> bool:
    """Check if a file is binary by looking for NULL bytes or non-text ratios."""
    try:
        with path.open("rb") as handle:
            chunk = handle.read(4096)
            if not chunk:
                return False
            # NULL byte is a strong indicator
            if b"\x00" in chunk:
                return True
            # High ratio of non-ascii/non-common-text bytes
            text_chars = bytearray({7, 8, 9, 10, 12, 13, 27} | set(range(0x20, 0x100)) - {0x7f})
            nontext = chunk.translate(None, text_chars)
            return len(nontext) / len(chunk) > 0.3
    except (OSError, PermissionError):
        return True


def ensure_directory(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def enumerate_files(
    root: Path,
    follow_links: bool = False,
    skip_directory: Optional[Callable[[Path], bool]] = None,
) -> Iterable[Path]:
    """Yield all files in root, handling circular symlinks and preventing duplicate file access."""
    root = normalize_path(root)
    # Use realpath/stat to detect duplicate files (different paths pointing to same inode)
    visited_nodes: Set[Tuple[int, int]] = set()
    stack: List[Path] = [root]

    while stack:
        current = stack.pop()
        try:
            # Sort entries for deterministic output
            entries = sorted(current.iterdir(), key=lambda item: item.name.lower())
            for entry in entries:
                try:
                    st = entry.stat(follow_symlinks=follow_links)
                    node_id = (st.st_dev, st.st_ino)
                except (OSError, PermissionError):
                    continue

                if node_id in visited_nodes:
                    continue
                
                is_link = entry.is_symlink()
                if is_link and not follow_links:
                    continue

                if entry.is_dir():
                    if skip_directory and skip_directory(entry):
                        continue
                    
                    visited_nodes.add(node_id)
                    stack.append(entry)
                elif entry.is_file():
                    visited_nodes.add(node_id)
                    yield entry
        except (PermissionError, OSError):
            continue
