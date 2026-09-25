from __future__ import annotations

import logging
import threading
from collections.abc import Generator

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings
from app.models.base import Base

logger = logging.getLogger(__name__)

SQLITE_FALLBACK_URL = "sqlite:///./app.db"

_engine: Engine | None = None
_session_factory: sessionmaker[Session] | None = None
_initialized = False
_init_lock = threading.Lock()


def _make_engine(url: str) -> Engine:
    if url.startswith("sqlite"):
        return create_engine(url, connect_args={"check_same_thread": False})
    # A short connect timeout keeps an unreachable server from stalling every request.
    return create_engine(
        url, pool_pre_ping=True, connect_args={"connect_timeout": get_settings().database_connect_timeout}
    )


def _use_engine(engine: Engine) -> None:
    global _engine, _session_factory
    _engine = engine
    _session_factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def get_engine() -> Engine:
    if _engine is None:
        init_db()
    assert _engine is not None
    return _engine


def get_session_factory() -> sessionmaker[Session]:
    if _session_factory is None:
        init_db()
    assert _session_factory is not None
    return _session_factory


def _add_missing_columns(engine: Engine) -> None:
    """Minimal forward-only migration: add nullable model columns that the database does not have yet.

    create_all() never alters existing tables, so databases created before a model gained new
    columns would otherwise fail on every query touching them.
    """
    inspector = inspect(engine)
    with engine.begin() as connection:
        for table in Base.metadata.sorted_tables:
            if not inspector.has_table(table.name):
                continue
            existing = {col["name"] for col in inspector.get_columns(table.name)}
            for column in table.columns:
                if column.name in existing or not column.nullable:
                    continue
                col_type = column.type.compile(dialect=engine.dialect)
                connection.execute(text(f"ALTER TABLE {table.name} ADD COLUMN {column.name} {col_type}"))


def init_db() -> None:
    """Connect to the configured database (falling back to SQLite) and create or migrate tables. Idempotent."""
    global _initialized
    with _init_lock:
        if _initialized:
            return
        import app.models  # noqa: F401  (register all models on Base.metadata)

        url = get_settings().database_url
        engine = _make_engine(url)
        try:
            with engine.connect() as connection:
                connection.execute(text("SELECT 1"))
        except Exception as exc:
            if url.startswith("sqlite"):
                raise
            logger.warning("Database %s is unreachable (%s); falling back to SQLite at %s",
                           engine.url.render_as_string(hide_password=True), exc.__class__.__name__, SQLITE_FALLBACK_URL)
            engine.dispose()
            engine = _make_engine(SQLITE_FALLBACK_URL)
        Base.metadata.create_all(bind=engine)
        _add_missing_columns(engine)
        _use_engine(engine)
        _initialized = True


def get_db_session() -> Generator[Session, None, None]:
    session = get_session_factory()()
    try:
        yield session
    finally:
        session.close()


def ping_database() -> bool:
    try:
        with get_engine().connect() as connection:
            connection.execute(text("SELECT 1"))
        return True
    except Exception:
        return False
