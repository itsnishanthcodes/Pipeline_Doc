from __future__ import annotations

from collections.abc import Generator

from sqlalchemy import create_engine, text
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


def init_db() -> None:
    global _initialized, _engine, _session_factory
    if _initialized:
        return
    try:
        engine = get_engine()
        Base.metadata.create_all(bind=engine)
    except Exception:
        # PostgreSQL is unreachable or timed out -> Fallback to SQLite instantly
        _engine = create_engine("sqlite:///./app.db", connect_args={"check_same_thread": False})
        _session_factory = sessionmaker(bind=_engine, autoflush=False, autocommit=False)
        Base.metadata.create_all(bind=_engine)
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

