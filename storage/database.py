"""Database connection setup and session management."""

from contextlib import contextmanager

from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from config import settings
from storage.models import Base

_engine = None
_SessionLocal = None
_dialect: str = "sqlite"  # Set at engine creation time; used by storage layer


def _create_engine(url: str | None = None):
    """Create SQLAlchemy engine with appropriate settings for the DB backend."""
    db_url = url or settings.db_url

    if db_url.startswith("sqlite"):
        engine = create_engine(
            db_url,
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )

        @event.listens_for(engine, "connect")
        def _set_sqlite_pragma(dbapi_conn, connection_record):
            cursor = dbapi_conn.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()
    else:
        engine = create_engine(
            db_url,
            pool_size=5,
            max_overflow=10,
        )
    return engine


def get_engine(url: str | None = None):
    """Get or create the global engine."""
    global _engine, _dialect
    if _engine is None:
        _engine = _create_engine(url)
        _dialect = _engine.dialect.name
    return _engine


def get_session_factory(url: str | None = None):
    """Get or create the global session factory."""
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(
            bind=get_engine(url), autocommit=False, autoflush=False
        )
    return _SessionLocal


@contextmanager
def get_session(url: str | None = None):
    """Context manager yielding a DB session with auto-commit/rollback."""
    factory = get_session_factory(url)
    session: Session = factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def init_db(url: str | None = None):
    """Create all tables. For dev/test only.

    # TODO: Replace create_all with Alembic migrations before first public deployment.
    # migrations/ directory is already scaffolded for this purpose.
    """
    engine = get_engine(url)
    Base.metadata.create_all(engine)


def reset_engine():
    """Reset the global engine and session factory. Used in tests."""
    global _engine, _SessionLocal, _dialect
    if _engine is not None:
        _engine.dispose()
    _engine = None
    _SessionLocal = None
    _dialect = "sqlite"
