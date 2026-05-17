"""
Antigravity Scanner Services Package.
Provides data persistence, configuration, logging, and history management.
"""

from antigravity.services.json_store import JSONStore
from antigravity.services.logger import setup_logging, get_logger
from antigravity.services.settings import SettingsManager
from antigravity.services.config import ConfigLoader

# Global instances
_json_store_instance = None
_settings_manager = None


def get_json_store(data_dir: str = "data") -> JSONStore:
    """Get or create the global JSON store instance."""
    global _json_store_instance
    if _json_store_instance is None:
        _json_store_instance = JSONStore(data_dir)
    return _json_store_instance


def get_settings_manager() -> SettingsManager:
    """Get or create the global settings manager instance."""
    global _settings_manager
    if _settings_manager is None:
        _settings_manager = SettingsManager(get_json_store())
    return _settings_manager


__all__ = [
    'JSONStore',
    'get_json_store',
    'SettingsManager', 
    'get_settings_manager',
    'ConfigLoader',
    'setup_logging',
    'get_logger',
]
