"""
Unit tests for the simplified service layer.
"""
import os
import tempfile
from pathlib import Path

import pytest
from antigravity.services.database import init_db, reset_engine, ScanRecord, get_session_context
from antigravity.services.settings import SettingsService
from antigravity.services.history import ScanHistoryService


@pytest.fixture(autouse=True)
def setup_test_db(tmp_path):
    """Setup an in-memory test database for each test."""
    reset_engine()
    os.environ["DATABASE_URL"] = "sqlite:///:memory:"
    init_db()
    yield
    reset_engine()


def test_settings_persistence():
    settings = SettingsService()
    settings.bootstrap()
    
    settings.set("theme", "light")
    assert settings.get("theme") == "light"
    
    settings.set_many({"default_mode": "multi"})
    assert settings.get("default_mode") == "multi"


def test_history_records(tmp_path):
    history = ScanHistoryService()
    
    # Create real directories
    root = tmp_path / "test_root"
    root.mkdir()
    out = tmp_path / "output"
    out.mkdir()
    
    # get_session is now a context manager
    with get_session_context() as session:
        record = ScanRecord(
            root_path=str(root),
            output_path=str(out),
            scan_mode="single",
            status="running",
        )
        session.add(record)
        session.commit()
        rec_id = record.id
    
    summary = {"files_processed": 10, "bytes_processed": 1024, "elapsed_seconds": 2.5}
    history.complete_record(rec_id, summary)
    
    records = history.get_all()
    latest = records[0]
    assert latest["files"] == 10
    assert latest["status"] == "completed"
    assert latest["elapsed"] == 2.5
