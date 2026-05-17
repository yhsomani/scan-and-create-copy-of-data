"""
Scan History Service — Tracks scan records in the database.
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from sqlalchemy import select
from antigravity.services.database import (
    ScanRecord, get_session_context
)


class DatabaseError(Exception):
    """Custom exception for database operations."""
    pass


class ScanHistoryService:
    """Persist and query scan records."""

    def create_record(
        self,
        root_path: str,
        output_path: str,
        mode: str = "single",
    ) -> int:
        p_root = Path(root_path)
        if not p_root.exists() or not p_root.is_dir():
            raise ValueError(f"ROOT_NOT_FOUND: {root_path}")

        try:
            with get_session_context() as session:
                record = ScanRecord(
                    root_path=root_path,
                    output_path=output_path,
                    scan_mode=mode,
                    status="running",
                )
                session.add(record)
                session.commit()
                return record.id
        except Exception as e:
            raise DatabaseError(f"Failed to create record: {e}") from e

    def complete_record(self, record_id: int, summary: Dict) -> None:
        try:
            with get_session_context() as session:
                record = session.get(ScanRecord, record_id)
                if record:
                    record.files_processed = summary.get("files_processed", 0)
                    record.files_skipped = summary.get("files_skipped", 0)
                    record.bytes_processed = summary.get("bytes_processed", 0)
                    record.elapsed_seconds = summary.get("elapsed_seconds", 0.0)
                    record.status = "completed"
        except Exception as e:
            import logging
            logging.getLogger("ScanHistory").error(f"Failed: {e}")

    def fail_record(self, record_id: int, error: str) -> None:
        try:
            with get_session_context() as session:
                record = session.get(ScanRecord, record_id)
                if record:
                    record.status = "failed"
                    record.error_message = error
        except Exception:
            pass

    def get_all(self, limit: int = 100) -> List[dict]:
        try:
            with get_session_context() as session:
                records = session.execute(
                    select(ScanRecord).order_by(ScanRecord.created_at.desc()).limit(limit)
                ).scalars().all()
                return [
                    {
                        "id": r.id,
                        "root_path": r.root_path,
                        "output_path": r.output_path,
                        "mode": r.scan_mode,
                        "files": r.files_processed,
                        "bytes": r.bytes_processed,
                        "elapsed": r.elapsed_seconds,
                        "status": r.status,
                        "created_at": r.created_at,
                    }
                    for r in records
                ]
        except Exception as e:
            import logging
            logging.getLogger("ScanHistory").error(f"Failed: {e}")
            return []

    def delete_record(self, record_id: int) -> None:
        try:
            with get_session_context() as session:
                record = session.get(ScanRecord, record_id)
                if record:
                    session.delete(record)
        except Exception:
            pass

    def get_stats(self) -> dict:
        try:
            with get_session_context() as session:
                total = session.query(ScanRecord).count()
                return {"total_scans": total}
        except Exception:
            return {"total_scans": 0}
