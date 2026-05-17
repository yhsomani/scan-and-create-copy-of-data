"""
Settings Service — Persistent key-value settings in JSON.
"""
from __future__ import annotations

from typing import Any, Dict, Optional

from antigravity.services.json_store import JSONStore


DEFAULTS: Dict[str, Any] = {
    "theme": "dark",
    "default_mode": "single",
    "default_format": "text",
    "default_workers": 4,
    "max_chunk_mb": 10.0,
    "max_output_files": 5,
    "skip_hidden": True,
    "allow_large_files": True,
    "last_target_path": "",
    "last_output_dir": "",
    "last_mode": "single",
}


class SettingsManager:
    """Key-value app settings persisted in JSON."""
    
    def __init__(self, store: JSONStore):
        self.store = store
        self._bootstrap()
    
    def _bootstrap(self):
        """Initialize default settings if not present."""
        for key, value in DEFAULTS.items():
            if self.store.get_setting(key) is None:
                self.store.set_setting(key, value, value_type=type(value).__name__)
    
    def get(self, key: str, fallback: Any = None) -> Any:
        """Get a setting value."""
        result = self.store.get_setting(key)
        if result is None:
            return DEFAULTS.get(key, fallback)
        
        # Return the value from the nested structure
        if isinstance(result, dict):
            return result.get('value', DEFAULTS.get(key, fallback))
        return result
    
    def set(self, key: str, value: Any) -> None:
        """Set a setting value."""
        value_type = type(value).__name__
        self.store.set_setting(key, value, value_type=value_type, category='general')
    
    def get_all(self) -> Dict[str, Any]:
        """Get all settings as a simple dict."""
        raw_settings = self.store.get_all_settings()
        result = {}
        for key, setting_data in raw_settings.items():
            if isinstance(setting_data, dict):
                result[key] = setting_data.get('value')
            else:
                result[key] = setting_data
        return result
    
    def set_many(self, data: Dict[str, Any]) -> None:
        """Set multiple settings at once."""
        for key, value in data.items():
            self.set(key, value)
    
    def reset_to_defaults(self):
        """Reset all settings to defaults."""
        for key, value in DEFAULTS.items():
            self.set(key, value)
