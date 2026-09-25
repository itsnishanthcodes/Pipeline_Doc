from __future__ import annotations

import threading
from collections.abc import Generator

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings
from app.models.base import Base

_engine: Engine | None = None
_session_factory: sessionmaker[Session] | None = None


def get_engine() -> Engine:
    global _engine
    if _engine is None:
        settings = get_settings()
        try:
            _engine = create_engine(settings.database_url, pool_pre_ping=True)
        except Exception:
            _engine = create_engine("sqlite:///./app.db", connect_args={"check_same_thread": False})
    return _engine


def get_session_factory() -> sessionmaker[Session]:
    global _session_factory
    if _session_factory is None:
        _session_factory = sessionmaker(bind=get_engine(), autoflush=False, autocommit=False)
    return _session_factory


_initialized = False
_init_lock = threading.Lock()


def _add_missing_columns(engine: Engine) -> None:
    """Minimal forward-only migration: add columns that exist on the models but not in the database.

    create_all() never alters existing tables, so databases created before a model gained new
    nullable columns would otherwise fail on every query touching them.
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
                connection.execute(text(f'ALTER TABLE {table.name} ADD COLUMN {column.name} {col_type}'))


def init_db() -> None:
    global _initialized, _engine, _session_factory
    with _init_lock:
        if _initialized:
            return
        _init_db_locked()


def _init_db_locked() -> None:
    global _initialized, _engine, _session_factory
    import app.models  # noqa: F401  (register all models on Base.metadata)

    try:
        engine = get_engine()
        Base.metadata.create_all(bind=engine)
    except Exception:
        # PostgreSQL is unreachable or timed out -> Fallback to SQLite instantly
        _engine = create_engine("sqlite:///./app.db", connect_args={"check_same_thread": False})
        _session_factory = sessionmaker(bind=_engine, autoflush=False, autocommit=False)
        engine = _engine
        Base.metadata.create_all(bind=engine)
    _add_missing_columns(engine)
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

