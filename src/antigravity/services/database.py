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
from typing import Optional

from sqlalchemy import (
    Boolean, Column, DateTime, Float, ForeignKey,
    Integer, String, Text, create_engine, event, text
)
from sqlalchemy.orm import DeclarativeBase, Session, relationship, sessionmaker, scoped_session


class Base(DeclarativeBase):
    pass




class ScanRecord(Base):
    __tablename__ = "scan_records"

    id: int = Column(Integer, primary_key=True, autoincrement=True)
    root_path: str = Column(String(512), nullable=False, index=True)
    output_path: str = Column(String(512), nullable=False, index=True)
    scan_mode: str = Column(String(32), default="single")

    files_processed: int = Column(Integer, default=0)
    files_skipped: int = Column(Integer, default=0)
    bytes_processed: int = Column(Integer, default=0)
    elapsed_seconds: float = Column(Float, default=0.0)
    status: str = Column(String(32), default="completed")  # running|completed|failed
    error_message: Optional[str] = Column(Text, nullable=True)
    created_at: datetime = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)







class AppSetting(Base):
    __tablename__ = "app_settings"

    id: int = Column(Integer, primary_key=True, autoincrement=True)
    key: str = Column(String(128), unique=True, nullable=False, index=True)
    value: str = Column(Text, nullable=True)
    description: str = Column(String(256), nullable=True)


# --------------------------------------------------------------------------- #
# Thread-Safe Engine & Session Factory
# --------------------------------------------------------------------------- #

_engine = None
_engine_lock = threading.Lock()
_SessionLocal = None
_session_lock = threading.Lock()


def _get_engine():
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
    """Return a thread-local scoped DB session (legacy compatibility + for use in services)."""
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
