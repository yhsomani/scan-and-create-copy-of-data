"""
Settings Service — Persistent key-value settings in SQLite.
"""
from __future__ import annotations

from typing import Dict

from sqlalchemy import select
from antigravity.services.database import (
    AppSetting, get_session_context
)


DEFAULTS: Dict[str, str] = {
    "theme": "dark",
    "default_mode": "single",
    "default_format": "text",
    "default_workers": "4",
    "max_chunk_mb": "10.0",
    "max_output_files": "5",
    "skip_hidden": "true",
    "allow_large_files": "true",
    "last_target_path": "",
    "last_output_dir": "",
    "last_mode": "single",
}


class SettingsService:
    """Key-value app settings persisted in SQLite."""

    def bootstrap(self) -> None:
        try:
            with get_session_context() as session:
                for key, value in DEFAULTS.items():
                    if not session.execute(select(AppSetting).filter_by(key=key)).scalars().first():
                        session.add(AppSetting(key=key, value=value))
        except Exception:
            pass

    def get(self, key: str, fallback: str = "") -> str:
        try:
            with get_session_context() as session:
                row = session.execute(select(AppSetting).filter_by(key=key)).scalars().first()
                return row.value if row else DEFAULTS.get(key, fallback)
        except Exception:
            return DEFAULTS.get(key, fallback)

    def set(self, key: str, value: str) -> None:
        try:
            with get_session_context() as session:
                row = session.execute(select(AppSetting).filter_by(key=key)).scalars().first()
                if row:
                    row.value = value
                else:
                    session.add(AppSetting(key=key, value=value))
        except Exception:
            pass

    def get_all(self) -> Dict[str, str]:
        try:
            with get_session_context() as session:
                rows = session.execute(select(AppSetting)).scalars().all()
                return {r.key: r.value for r in rows}
        except Exception:
            return {}

    def set_many(self, data: Dict[str, str]) -> None:
        for key, value in data.items():
            self.set(key, value)
