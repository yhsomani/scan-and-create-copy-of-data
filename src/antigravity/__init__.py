"""
Antigravity Scanner - High-performance codebase scanner and text extractor.

A production-grade tool for scanning massive repositories (100GB+),
extracting readable text content for LLM/RAG preparation, and providing
powerful post-scan organization tools.
"""

__version__ = "2.0.0"
__author__ = "Antigravity Team"
__email__ = "dev@antigravity.local"

# Core exports - lazy imports to avoid circular dependencies
__all__ = [
    "__version__",
    "__author__",
    "__email__",
]


def __getattr__(name: str):
    """Lazy loading of module attributes."""
    if name == "Scanner":
        from antigravity.core.scanner import DirectoryScanner
        return DirectoryScanner
    elif name == "ScanConfig":
        from antigravity.services.config import ScanConfig
        return ScanConfig
    elif name == "FileFilter":
        from antigravity.core.filters import FileFilter
        return FileFilter
    elif name == "DatabaseService":
        from antigravity.services.database import DatabaseService
        return DatabaseService
    elif name == "get_db_path":
        from antigravity.services.database import get_db_path
        return get_db_path
    raise AttributeError(f"module {__name__!r} has no attribute {__name__!r}")