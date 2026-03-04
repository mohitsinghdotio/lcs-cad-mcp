"""SQLite engine and session factory for the archive database."""
from __future__ import annotations

import logging
from contextlib import contextmanager
from pathlib import Path

logger = logging.getLogger(__name__)

_engine = None
_SessionLocal = None


def _get_archive_path() -> Path:
    """Get archive path from settings or fall back to a default."""
    try:
        from lcs_cad_mcp.settings import Settings
        return Settings().archive_path
    except Exception:
        return Path.home() / ".lcs_cad_mcp" / "archive"


def get_engine():
    """Get or create the SQLite engine (lazy initialization)."""
    global _engine
    if _engine is None:
        from sqlalchemy import create_engine

        archive_path = _get_archive_path()
        archive_path.mkdir(parents=True, exist_ok=True)
        db_path = archive_path / "archive.db"

        # check_same_thread=False is safe because SQLAlchemy session management handles thread safety
        _engine = create_engine(
            f"sqlite:///{db_path}",
            echo=False,
            future=True,
            connect_args={"check_same_thread": False},
        )
        logger.info("Archive SQLite engine initialized at %s", db_path)
    return _engine


def get_session_local():
    """Get or create the session factory."""
    global _SessionLocal
    if _SessionLocal is None:
        from sqlalchemy.orm import sessionmaker
        _SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=get_engine())
    return _SessionLocal


# Module-level SessionLocal (created lazily)
class _LazySessionFactory:
    def __call__(self, *args, **kwargs):
        return get_session_local()(*args, **kwargs)


SessionLocal = _LazySessionFactory()


@contextmanager
def get_db_session():
    """ACID transaction context manager for all repository operations."""
    session = get_session_local()()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
