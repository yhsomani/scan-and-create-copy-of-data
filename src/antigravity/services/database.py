"""
Database layer: SQLAlchemy models + session factory.
Supports SQLite by default, PostgreSQL via DATABASE_URL env var.
Thread-safe singleton pattern for engine and session factory.
"""
from __future__ import annotations

import os
import threading
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Optional, List, Any

from sqlalchemy import (
    Boolean, Column, DateTime, Float, ForeignKey, Index,
    Integer, String, Text, create_engine, event, text
)
from sqlalchemy.orm import (
    DeclarativeBase, Session, relationship, sessionmaker, 
    scoped_session, Mapped, mapped_column
)


class Base(DeclarativeBase):
    pass


class ScanRecord(Base):
    """Tracks scan history, metrics, and status."""
    __tablename__ = "scan_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    root_path: Mapped[str] = mapped_column(String(512), nullable=False, index=True)
    output_path: Mapped[str] = mapped_column(String(512), nullable=False, index=True)
    scan_mode: Mapped[str] = mapped_column(String(32), default="single")
    
    # Metrics
    files_scanned: Mapped[int] = mapped_column(Integer, default=0)
    files_processed: Mapped[int] = mapped_column(Integer, default=0)
    files_skipped: Mapped[int] = mapped_column(Integer, default=0)
    bytes_processed: Mapped[int] = mapped_column(Integer, default=0)
    lines_processed: Mapped[int] = mapped_column(Integer, default=0)
    errors_count: Mapped[int] = mapped_column(Integer, default=0)
    elapsed_seconds: Mapped[float] = mapped_column(Float, default=0.0)
    
    # Status
    status: Mapped[str] = mapped_column(String(32), default="completed")
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Config snapshot
    config_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc), index=True
    )
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime, default=None, onupdate=lambda: datetime.now(timezone.utc)
    )
    
    # Relationships
    files: Mapped[List["ScanFile"]] = relationship(
        "ScanFile", back_populates="scan_record", cascade="all, delete-orphan"
    )


class ScanFile(Base):
    """Granular file-level tracking for resume/analytics."""
    __tablename__ = "scan_files"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    scan_id: Mapped[int] = mapped_column(Integer, ForeignKey("scan_records.id"), nullable=False, index=True)
    
    # File info
    relative_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    absolute_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    extension: Mapped[str] = mapped_column(String(64), nullable=True, index=True)
    
    # Metrics
    size_bytes: Mapped[int] = mapped_column(Integer, default=0)
    lines_count: Mapped[int] = mapped_column(Integer, default=0)
    encoding: Mapped[str] = mapped_column(String(64), nullable=True)
    
    # Output info
    output_file: Mapped[str] = mapped_column(String(512), nullable=True)
    part_number: Mapped[int] = mapped_column(Integer, default=1)
    
    # Status
    processed: Mapped[bool] = mapped_column(Boolean, default=True)
    skipped: Mapped[bool] = mapped_column(Boolean, default=False)
    skip_reason: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Hash for incremental cache
    file_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
    
    # Timestamp
    processed_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )
    
    # Relationships
    scan_record: Mapped["ScanRecord"] = relationship("ScanRecord", back_populates="files")


class ScanConfigProfile(Base):
    """Saved scan configuration profiles."""
    __tablename__ = "scan_config_profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(128), unique=True, nullable=False, index=True)
    description: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    
    # Config as JSON
    config_json: Mapped[str] = mapped_column(Text, nullable=False)
    
    # Metadata
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime, default=None, onupdate=lambda: datetime.now(timezone.utc)
    )


class AppSetting(Base):
    """Application settings and preferences."""
    __tablename__ = "app_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    key: Mapped[str] = mapped_column(String(128), unique=True, nullable=False, index=True)
    value: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    value_type: Mapped[str] = mapped_column(String(32), default="string")
    description: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    category: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime, default=None, onupdate=lambda: datetime.now(timezone.utc)
    )


# --------------------------------------------------------------------------- #
# Thread-Safe Engine & Session Factory
# --------------------------------------------------------------------------- #

_engine = None
_engine_lock = threading.Lock()
_SessionLocal = None
_session_lock = threading.Lock()


def _get_engine():
    """Get or create the database engine (singleton pattern)."""
    global _engine
    if _engine is None:
        with _engine_lock:
            if _engine is None:
                url = os.getenv("DATABASE_URL", "sqlite:///antigravity_scanner.db")
                is_sqlite = "sqlite" in url
                _engine = create_engine(
                    url,
                    echo=False,
                    connect_args={"check_same_thread": False} if is_sqlite else {},
                    pool_pre_ping=True,
                )
                if is_sqlite:
                    @event.listens_for(_engine, "connect")
                    def _set_sqlite_pragma(dbapi_conn, _):
                        cursor = dbapi_conn.cursor()
                        cursor.execute("PRAGMA journal_mode=WAL")
                        cursor.execute("PRAGMA foreign_keys=ON")
                        cursor.close()
    return _engine


def init_db() -> None:
    """Create all tables and drop deprecated ones. Safe to call multiple times."""
    engine = _get_engine()
    
    # Drop deprecated security_findings table if it exists
    from sqlalchemy import inspect
    inspector = inspect(engine)
    if "security_findings" in inspector.get_table_names():
        with engine.connect() as conn:
            conn.execute(text("DROP TABLE security_findings"))
            conn.commit()

    Base.metadata.create_all(bind=engine)


@contextmanager
def get_session_context():
    """Thread-safe context manager for database sessions."""
    global _SessionLocal
    if _SessionLocal is None:
        with _session_lock:
            if _SessionLocal is None:
                factory = sessionmaker(bind=_get_engine(), autoflush=False, autocommit=False)
                _SessionLocal = scoped_session(factory)
    
    session = _SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def get_session() -> Session:
    """Return a thread-local scoped DB session."""
    global _SessionLocal
    if _SessionLocal is None:
        with _session_lock:
            if _SessionLocal is None:
                factory = sessionmaker(bind=_get_engine(), autoflush=False, autocommit=False)
                _SessionLocal = scoped_session(factory)
    return _SessionLocal()


def reset_engine() -> None:
    """Internal use for testing only."""
    global _engine, _SessionLocal
    with _engine_lock:
        _engine = None
    with _session_lock:
        _SessionLocal = None
