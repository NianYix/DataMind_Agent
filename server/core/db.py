from __future__ import annotations

from collections.abc import Generator

from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from server.core.config import get_settings


class Base(DeclarativeBase):
    pass


settings = get_settings()
connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
engine = create_engine(settings.database_url, connect_args=connect_args, future=True)


if settings.database_url.startswith("sqlite"):

    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record) -> None:  # noqa: ARG001
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    from server import models  # noqa: F401

    Base.metadata.create_all(bind=engine)
    _migrate_sqlite_v2()


def _migrate_sqlite_v2() -> None:
    """Add columns to existing SQLite databases (create_all won't alter)."""
    if not settings.database_url.startswith("sqlite"):
        return
    stmts = [
        ("datasets", "source_type", "ALTER TABLE datasets ADD COLUMN source_type VARCHAR(50) DEFAULT 'file'"),
        ("datasets", "table_name", "ALTER TABLE datasets ADD COLUMN table_name VARCHAR(255)"),
        ("datasets", "connection_id", "ALTER TABLE datasets ADD COLUMN connection_id VARCHAR(36)"),
        ("agent_runs", "estimated_cost", "ALTER TABLE agent_runs ADD COLUMN estimated_cost FLOAT"),
        ("agent_runs", "cancel_requested", "ALTER TABLE agent_runs ADD COLUMN cancel_requested BOOLEAN DEFAULT 0"),
    ]
    with engine.begin() as conn:
        for table, column, ddl in stmts:
            rows = conn.exec_driver_sql(f"PRAGMA table_info({table})").fetchall()
            existing = {r[1] for r in rows}
            if column not in existing:
                conn.exec_driver_sql(ddl)
