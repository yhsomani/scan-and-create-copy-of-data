from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from antigravity.services.config import ScanConfig
from antigravity.utils.file_utils import (
    PathEscapeError,
    load_ignore_patterns,
    matches_ignore_patterns,
    normalize_path,
    safe_is_binary,
    is_hidden_path,
    validate_pathsafety,
)


# Directories that are always skipped during traversal
SKIP_DIRS = {
    # VCS
    ".git",
    ".hg",
    ".svn",
    # Package / environment
    "node_modules",
    "venv",
    ".venv",
    "env",
    # Build artifacts
    "bin",
    "obj",
    "dist",
    "build",
    "target",
    "out",
    ".egg-info",
    # Python caches
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    # Framework caches
    ".next",
    ".nuxt",
    ".output",
    # IDE / OS
    ".idea",
    ".vscode",
    ".DS_Store",
    # Dependencies
    "vendor",
    ".bundle",
}

# Binary / non-text extensions that are never useful to extract
SKIP_EXTENSIONS = {
    # Executables & libraries
    ".exe", ".dll", ".so", ".dylib", ".a", ".lib", ".o", ".obj",
    # Java archives
    ".class", ".jar", ".war", ".ear", ".dex",
    # Compressed archives
    ".zip", ".tar", ".gz", ".7z", ".rar", ".bz2", ".xz",
    # Images
    ".png", ".jpg", ".jpeg", ".gif", ".bmp", ".svg", ".ico", ".webp", ".tiff",
    # Documents
    ".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx",
    # Media
    ".mp3", ".mp4", ".wav", ".avi", ".mov", ".mkv", ".webm",
    # Fonts
    ".woff", ".woff2", ".ttf", ".otf", ".eot",
    # Source maps
    ".map",
    # Compiled Python
    ".pyc", ".pyo", ".pyd",
    # Misc binary
    ".res", ".suo", ".pdb",
    # Lock / swap / temp
    ".lock", ".swp", ".tmp",
}

# Lock files that should always be skipped (exact filename match)
SKIP_FILE_NAMES = {
    "package-lock.json",
    "yarn.lock",
    "pnpm-lock.yaml",
    "pipfile.lock",
    "poetry.lock",
    "composer.lock",
    "bun.lockb",
    "npm-shrinkwrap.json",
    "go.sum",
}

# Extensions that are considered "useful" source / config files
USEFUL_EXTENSIONS = {
    # Python
    ".py", ".pyw",
    # JavaScript / TypeScript
    ".js", ".jsx", ".ts", ".tsx",
    # JVM
    ".java", ".kt",
    # .NET
    ".cs",
    # Systems
    ".go", ".rs", ".c", ".h", ".cpp", ".hpp",
    # Scripting
    ".rb", ".php", ".swift",
    # Web
    ".html", ".css", ".scss", ".sass", ".less",
    # Config
    ".json", ".yaml", ".yml", ".toml", ".ini", ".cfg", ".conf", ".xml",
    # Data / query
    ".sql", ".graphql", ".gql",
    # Documentation / markup
    ".md", ".markdown", ".txt", ".rst", ".adoc",
    # Shell / scripts
    ".sh", ".ps1", ".bat",
    # Env
    ".env",
}

# Well-known filenames that should always be included regardless of extension
USEFUL_FILE_NAMES = {
    "dockerfile",
    "makefile",
    "cmakelists.txt",
    "license",
    "license.md",
    "license.txt",
    "readme",
    "readme.md",
    "readme.txt",
    ".gitignore",
    ".gitattributes",
    ".editorconfig",
    ".env",
    ".env.example",
    "requirements.txt",
    "pyproject.toml",
    "setup.py",
    "setup.cfg",
    "package.json",
    "tsconfig.json",
    "angular.json",
    "vite.config.ts",
    "vite.config.js",
    "cargo.toml",
    "go.mod",
    "gemfile",
    "rakefile",
    "build.gradle",
    "settings.gradle",
    "pom.xml",
}

# Generated / minified file suffixes to always skip
GENERATED_VARIANTS = (".min.js", ".min.css", ".bundle.js", ".chunk.js")

# Default safety limit for maximum single-file size (bytes)
MAX_FILE_SIZE_BYTES = 100 * 1024 * 1024  # 100 MB


@dataclass
class FileFilter:
    """Decides which files and directories to include or exclude from a scan."""

    config: ScanConfig
    ignore_patterns: Iterable[str] = None

    def __post_init__(self) -> None:
        if self.ignore_patterns is None:
            self.ignore_patterns = load_ignore_patterns(
                self.config.root, self.config.ignore_file_name
            )

    def should_skip_directory(self, directory: Path) -> bool:
        """Return ``True`` if *directory* should be entirely skipped."""
        directory = normalize_path(directory)
        if not validate_pathsafety(directory, self.config.root):
            raise PathEscapeError(f"Directory escapes root boundary: {directory}")
        
        if (
            directory == self.config.output_dir
            or self.config.output_dir in directory.parents
        ):
            return True
        name = directory.name.lower()
        if name in SKIP_DIRS:
            return True
        if self.config.skip_hidden and is_hidden_path(directory):
            return True
        if matches_ignore_patterns(directory, self.config.root, self.ignore_patterns):
            return True
        return False

    def should_process_file(self, path: Path) -> bool:
        """Return ``True`` if *path* should be read and written to output."""
        path = normalize_path(path)
        if not validate_pathsafety(path, self.config.root):
            raise PathEscapeError(f"File path escapes root boundary: {path}")

        if path == self.config.error_file or self.config.output_dir in path.parents:
            return False
        name = path.name
        name_lower = name.lower()
        ext = path.suffix.lower()

        if matches_ignore_patterns(path, self.config.root, self.ignore_patterns):
            return False
        if self.config.skip_hidden and is_hidden_path(path):
            return False
        if name_lower in SKIP_FILE_NAMES:
            return False
        if ext in SKIP_EXTENSIONS:
            return False
        if any(name_lower.endswith(variant) for variant in GENERATED_VARIANTS):
            return False

        # Safety limit: skip files larger than 100 MB unless explicitly allowed
        if not self.config.allow_large_files:
            try:
                if path.stat().st_size > MAX_FILE_SIZE_BYTES:
                    return False
            except OSError as e:
                import logging
                logging.getLogger("scan").debug(f"Could not stat {path}: {e}")
                return False

        if name_lower in USEFUL_FILE_NAMES:
            return True
        return ext in USEFUL_EXTENSIONS and not safe_is_binary(path)
